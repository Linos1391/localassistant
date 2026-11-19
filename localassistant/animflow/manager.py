#pylint:disable=E0611:no-name-in-module
"""Emotion class manipulator."""
from pathlib import Path
import sys
import socket
from threading import Event, Thread, current_thread
from queue import Queue
from time import monotonic, sleep

from PyQt6.QtCore import QProcess

from animflow import Animation
from animflow.parser import CommandMap, SocketParser, DEFAULT_HOST, DEFAULT_PORT

from localassistant.utils import Constant

class AnimationFolder:
    """Label for animation's folders."""
    EMOTIONS = "emotions"
    ACTIONS = "actions"

    @staticmethod
    def convert_to_path(folder_name: str):
        """Convert the folder into `pathlib.Path`"""
        return Path(__file__).parent / folder_name

    @classmethod
    def get_all_folders(cls) -> list[Path]:
        """Get all folders."""
        return [
            cls.convert_to_path(value) for name, value in vars(cls).items()
            if not name.startswith("_") and isinstance(value, str)
        ]

class EmotionManipulator(QProcess):
    """The emotion manipulator."""
    animations: dict[str, list[str]]
    current_emotion: str

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT
    ) -> None:
        super().__init__()

        self._socket_alive = False
        self._socket_requests = Queue()

        animation_folders: list[Path] = AnimationFolder.get_all_folders()

        self.animations = {}
        for folder in animation_folders:
            animations: list[str] = []
            for animation in Animation.load_recur(folder):
                animations.append(animation.name)
            self.animations.update({folder.name: animations})

        animflow_args: list[str] = [
            "-m", "animflow.parser",
            "--host", host,
            "--port", str(port),
            "--animation", ",".join(map(str, animation_folders))
        ]
        self.start(sys.executable, arguments=animflow_args)

        self._socket_thread = Thread(
            target=self._socket_client,
            kwargs={"host": host, "port": port},
            daemon=True
        )
        self._socket_thread.start()

        self.set_emotion(Constant.DEFAULT_EMOTION, raise_error=True)
        self.display()

    def _send_command(self, cmd: str, **kwargs):
        response_ready = Event()
        response = {}
        self._socket_requests.put(((cmd, kwargs), response, response_ready))

        response_ready.wait()
        return response

    def _socket_client(self, host: str, port: int):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        deadline = monotonic() + Constant.ANIMFLOW_TIMEOUT
        while True:
            try:
                client.connect((host, port))
                break
            except ConnectionRefusedError as err:
                if monotonic() >= deadline:
                    client.close()
                    self.kill_process()
                    raise ConnectionError(
                        f"Animflow did not start listening on {host}:{port}."
                    ) from err
                sleep(0.1)

        with client:
            self._socket_alive = True
            while self._socket_alive:
                try:
                    request = self._socket_requests.get_nowait()
                except Exception: #pylint:disable=W0718:broad-exception-caught
                    sleep(0.1)
                    continue

                (cmd, kwargs), response, response_ready = request
                SocketParser.send_command(client, cmd, **kwargs)

                recv_data = SocketParser.recv_json(client)
                response.update(recv_data)
                response_ready.set()
                if not recv_data:
                    break

    @property
    def is_alive(self):
        """Does the socket alive or not"""
        return self._socket_alive

    def set_emotion(self, emotion: str, raise_error: bool = False):
        """Set the current emotion."""
        if emotion in self.animations.get(AnimationFolder.EMOTIONS, []):
            response = self._send_command(CommandMap.SELECT, animation_name=emotion, loop=True) #FIXME - not looping
            self.current_emotion: str = emotion
            return response
        elif raise_error:
            raise OSError(f"Animation {emotion} cannot be found.")

    def activate_action(self, action: str, raise_error: bool = False):
        """Set the action up."""
        if action in self.animations.get(AnimationFolder.ACTIONS, []):
            return self._send_command(CommandMap.SELECT, animation_name=action)
        elif raise_error:
            raise OSError(f"Animation {action} cannot be found.")

    def deactivate_action(self):
        """Disable the action and set the last emotion up again."""
        return self.set_emotion(self.current_emotion)

    def load_more_animation(self, animation_path: str | Path):
        """Load more animation into the displayer."""
        return self._send_command(CommandMap.LOAD, animation=animation_path)

    def display(self):
        """Display via animflow."""
        return self._send_command(CommandMap.DISPLAY)

    def stop_display(self):
        """Stop displaying."""
        return self._send_command(CommandMap.STOP_DISPLAY)

    def kill_process(self):
        """Kill the socket. The manipulator is now un-reusable."""
        self._socket_alive = False
        if current_thread() is not self._socket_thread:
            self._socket_thread.join()
        self.kill()

EmotionManipulator()
