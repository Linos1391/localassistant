"""Chat models."""
import os
from pathlib import Path
import socket
import logging
import time
from datetime import datetime

import psutil

from PyQt6.QtCore import QProcess, QIODevice #pylint:disable=E0611:no-name-in-module

from haystack.components.builders import PromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage, ChatRole, StreamingCallbackT, StreamingChunk #pylint:disable=W0611:unused-import
from haystack.utils import Secret

from localassistant.models.tools import toolset
from localassistant.utils import LocasException, UtilsMethod, Constant, PATH

LOGGER = logging.getLogger(__name__)

class LlamaCppServer(QProcess):
    """Init the server on port we need..."""
    LOADED_PHRASE: str = "llama_server: model loaded"

    def __init__(
        self,
        llama_bin_path: str,
        model_path: str,
        mmproj_path: str = "",
        lora_paths: list[str] | None = None,
        llama_tools_enable: bool = False,
        port: int = Constant.DEFAULT_LLAMA_PORT
    ) -> None:
        super().__init__()
        self.log_file: str = str(PATH.env / "llama.log")
        self.setStandardOutputFile(self.log_file, QIODevice.OpenModeFlag.Truncate)
        self.setStandardErrorFile(self.log_file, QIODevice.OpenModeFlag.Append)

        self.port: int = port
        self._check_port_in_use()

        llama_execution: str = ""
        llama_arguments: list = [
            "--model", model_path,
            "--port", str(port),
            "--image-min-tokens", "1024", "--no-ui"
        ]
        if mmproj_path:
            llama_arguments += ["--mmproj", mmproj_path]
        if lora_paths:
            for lora_path in lora_paths:
                llama_arguments += ["--lora", lora_path]
        if llama_tools_enable:
            llama_arguments += ["--tools", "all"]

        for llama in ("llama-server", "llama-server.exe", "llama", "llama.exe"):
            _path: Path = Path(llama_bin_path) / llama
            if _path.exists():
                llama_execution = str(_path)
                if llama.find("-server") == -1:
                    llama_arguments.insert(0, "serve")
                break
        assert llama_execution, ("The agent requires an available llama.cpp path to work. "
                                f"Is '{llama_bin_path}' the correct path to the bin folder?")

        self.start(llama_execution, llama_arguments)

    def _check_port_in_use(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", self.port))
        except OSError as err:
            raise LocasException(f"Port {self.port} is already in use. Please change the port "
                                 "or enable kill on start.") from err

    @staticmethod
    def kill_process_by_port(port: int = Constant.DEFAULT_LLAMA_PORT):
        """Kills all processes on the specified port. Usually 8000 as llama.cpp server."""
        for conn in psutil.net_connections(kind='inet'):
            if isinstance(conn.laddr, tuple) and len(conn.laddr) >= 2 and conn.laddr.port == port:
                process = psutil.Process(conn.pid)
                LOGGER.info("Killed port: %i", port)
                try:
                    if conn.pid:
                        process.terminate()
                        process.wait(timeout=3)
                except psutil.AccessDenied:
                    process.kill()
                except psutil.NoSuchProcess:
                    continue

    def check_model_loaded(self):
        """Will finish when the model loaded"""
        with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                if self.LOADED_PHRASE in line.lower():
                    break

class LocasAgent(Agent):
    """Chat extension.

    Args:
        model_path (str): The path to model snapshot.
    """
    def __init__(
        self,
        port: int = Constant.DEFAULT_LLAMA_PORT,
        streaming_callback: StreamingCallbackT | None = None,
        **generation_kwargs
    ) -> None:
        """Chat extension"""
        self.docs: list[str] = []
        self.chat_message: list[ChatMessage] = []
        self.builder: PromptBuilder = PromptBuilder(
            Constant.TEMPLATE,
            required_variables=["query"]
        )

        super().__init__(
            chat_generator=OpenAIChatGenerator(
                model="",
                api_key=Secret.from_token("Not Implement"),
                api_base_url=f"http://localhost:{port}/v1",
                generation_kwargs=generation_kwargs,
            ),
            streaming_callback=streaming_callback,
            tools=toolset,
        )
        self.warm_up()

    def agent_chat(self, max_chat_message: int = Constant.DEFAULT_MAX_CHAT_MESSAGE) -> str:
        """Run the agent with existing chat message. Update chat message beforehand."""
        chat_message: list[ChatMessage] = []
        if len(self.chat_message) > max_chat_message:
            if self.chat_message[0].is_from(ChatRole.SYSTEM):
                chat_message = [self.chat_message[0]] + self.chat_message[-max_chat_message+1:]
            else:
                chat_message = self.chat_message[-max_chat_message:]
        else:
            chat_message = self.chat_message

        result = self.run(chat_message)
        self.chat_message = result.get("messages", [])
        last_message = result.get("last_message")

        if last_message is None:
            raise LocasException("Cannot extract response from agent.")
        return last_message._content[0].text # type:ignore pylint:disable=W0212:protected-access

    def chat_to_history(self, filename: str = "") -> str:
        """Convert its chat message and save to history json file. Return the file name."""
        if filename:
            file, _ = os.path.splitext(filename)
            path = PATH.histories / f"{file}.json"
        else:
            path = UtilsMethod.validate_filename(
                PATH.histories / f"{datetime.now().strftime("%Y-%m-%d_%H.%M.%S")}.json"
            )

        UtilsMethod.write_json(path, [msg.to_openai_dict_format() for msg in self.chat_message])
        return str(path)

    def history_to_chat(self, filename: str, starred: bool = False):
        """Convert history json data and import into its chat message."""
        self.chat_message = [
            ChatMessage.from_openai_dict_format(msg) for msg in UtilsMethod.read_json(
                Constant.STARRED_DIR / filename if starred else PATH.histories / filename
            )
        ]
