#pylint: disable=E0611:no-name-in-module W0212:protected-access
"""The Chat tab."""
import os
from pathlib import Path
import logging
import shutil
import re
import queue
import threading
from typing import Callable, Literal, Any

from haystack.components.converters.image import ImageFileToImageContent
from haystack.hooks.human_in_the_loop import ConfirmationUIResult
from PyQt6.QtWidgets import (QWidget, QPushButton, QPlainTextEdit, QComboBox, QBoxLayout, QTextEdit,
                             QScrollArea, QFileDialog, QListWidget, QDialog, QDialogButtonBox)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel
from PyQt6.QtCore import QObject, QModelIndex, pyqtSignal, pyqtSlot

from pyqt6_multiselect_combobox import MultiSelectComboBox

from localassistant.models.chat import (LlamaCppServer, LocasAgent, ChatMessage, ChatRole,
                                        StreamingChunk)
from localassistant.models.docs import LocasDocs
from localassistant.models.tools import ToolValidator
from localassistant.utils import (Constant, ModelGuide, ModelMetadata, UIFiles, SettingKey,
                                  PATH, LocasException)
from localassistant.qt_gui.worker import Worker
from localassistant.qt_gui.item_button_delegate import ItemButtonDelegate

LOGGER = logging.getLogger(__name__)

class UILabel:
    """Managing ui name tag so that it can be called easier."""
    SYSTEM_CHAT_MESSAGE = "systemChatMessage"
    USER_CHAT_MESSAGE = 'userChatMessage'
    ASSISTANT_CHAT_MESSAGE = "assistantChatMessage"
    CHAT_SCROLL_AREA = "chatScrollArea"
    CHAT_SCROLL_CONTENTS = "chatScrollContents"
    CHAT_HISTORY = "chatHistory"
    DOCS_BUTTON = "docsButton"
    RESET_BUTTON = "resetButton"
    CHAT_LOAD_BUTTON = "chatLoadButton"
    DOCS_LOAD_BUTTON = "docsLoadButton"
    STEP_GENERATION_BUTTON = "stopGenerationButton"
    TOOL_BUTTON = "toolButton"
    TOOL_DESCRIPTION = "toolDescription"

class StreamingDispatcher(QObject):
    """So that it wont freeze :("""
    flush = pyqtSignal()

class QtHumanInTheLoop(QObject):
    """Human in the loop. Yes just as we all need"""
    show_dialog = pyqtSignal(str, str, dict)

    def __init__(self, self_widget) -> None:
        super().__init__()
        self.action: Literal["confirm", "reject"] = "confirm"
        self._result_ready = threading.Event()
        self._result: ConfirmationUIResult | None = None

        self.dialog = QDialog(self_widget)
        self_widget._load_ui(UIFiles.CHAT_HITL, self.dialog)
        self.description: QTextEdit = self_widget._get(self.dialog, UILabel.TOOL_DESCRIPTION)

        button_box: QDialogButtonBox = self_widget._get(self.dialog, UILabel.TOOL_BUTTON)
        button_box.accepted.connect(lambda: self._complete("confirm"))
        button_box.rejected.connect(lambda: self._complete("reject"))

        self.show_dialog.connect(self._show_dialog)

    def _complete(self, action: Literal["confirm", "reject"]) -> None:
        self.action = action
        self._result = ConfirmationUIResult(action=action)
        self._result_ready.set()
        self.dialog.accept()

    @pyqtSlot(str, str, dict)
    def _show_dialog(self, tool_name: str, tool_description: str,
                     tool_params: dict[str, Any]) -> None:
        self.description.setMarkdown(
            f"**TOOL NAME:** {tool_name}"
            f"{Constant.MESSAGE_LINE_BREAK}"
            f"**TOOL PARAMS:** {tool_params}"
            f"{Constant.MESSAGE_LINE_BREAK}"
            f"**TOOL DESCRIPTION:** {tool_description}"
        )
        self.dialog.open()

    def get_user_confirmation(
        self,
        tool_name: str,
        tool_description: str,
        tool_params: dict[str, Any]
    ) -> ConfirmationUIResult:
        """Required for it."""
        self._result_ready.clear()
        self._result = None

        self.show_dialog.emit(tool_name, tool_description, tool_params)

        self._result_ready.wait()
        return self._result or ConfirmationUIResult(action=self.action)

def _chat_tab_setup(self):
    def __system_setup():
        system_message.setPlainText(Constant.DEFAULT_SYSTEM_MESSAGE)

    def __system_drag_enter(e: QDragEnterEvent | None):
        if e is None:
            return
        data = e.mimeData()
        if data and data.hasUrls() and data.urls()[0].toLocalFile().endswith(".txt"):
            e.acceptProposedAction()
        else:
            e.ignore()

    def __system_drop(e: QDropEvent | None):
        if e is None:
            return
        data = e.mimeData()
        if data:
            for url in data.urls():
                try:
                    with open(url.toLocalFile(), "r", encoding="utf-8") as f:
                        system_message.setPlainText(f.read())
                        f.close()
                except Exception as err: #pylint:disable=W0718:broad-exception-caught
                    system_message.setPlainText(f"Error reading file: {err}.")

    def __set_up_agent(do_func: Callable[[], None]):
        def ___conditional_do_func(condition: bool, remove_func: Callable):
            if condition:
                do_func()
                remove_func()

        chat_load_button.setEnabled(False)

        if getattr(self, "agent", None) is None:
            model_meta: ModelMetadata = ModelGuide.AGENT.value
            model_name: str = self._get_model_name(model_meta.role[0], model_meta.url)
            if not model_name:
                self._show_error((AssertionError, "Cannot access to a valid agent."))
                return

            kwargs: dict = {}
            mmproj_name: str = self._get_model_name(model_meta.role[1], model_meta.url,
                                                    show_error = False)
            if mmproj_name:
                kwargs.update({
                    "mmproj_path": self._direct_to_model_name(model_meta.tag, mmproj_name)
                })

            lora_meta: ModelMetadata = ModelGuide.AGENT_LORA.value
            lora_name: str = self._get_model_name(lora_meta.role[0], lora_meta.url,
                                                  show_error = False)
            if lora_name:
                lora_combo_box = self.setting_model_combo_box.get(lora_meta.role[0])
                if isinstance(lora_combo_box, MultiSelectComboBox):
                    kwargs.update({
                        "lora_paths": list(map(
                            lambda name: self._direct_to_model_name(lora_meta.tag, name),
                            lora_name.split(lora_combo_box.getDisplayDelimiter())
                        ))
                    })

            system_message.setEnabled(False)
            msg = f"Load agent model: {model_name}"
            LOGGER.info(msg)
            _remove = self._show_notify(msg)

            if self.setting.data[SettingKey.LLAMA_PORT_KILL]:
                LlamaCppServer.kill_process_by_port(self.setting.data[SettingKey.LLAMA_PORT])

            llama_server_process = LlamaCppServer(
                llama_bin_path=self.setting.data.get(SettingKey.LLAMA_CPP_BIN, ""),
                model_path=self._direct_to_model_name(model_meta.tag, model_name),
                port=self.setting.data[SettingKey.LLAMA_PORT],
                llama_kwargs=self.setting.data.get(SettingKey.LLAMA_KWARGS, "").strip().split(),
                **kwargs
            )
            self.processes.append(llama_server_process)

            llama_worker = Worker(fn=llama_server_process.check_model_loaded)
            llama_worker.signal.error_signal.connect(
                lambda err: (__chat_message_error(err, None, None))
            )
            llama_worker.signal.result_signal.connect(
                lambda: (
                    chat_load_button.setText(Constant.BUTTON_UNLOAD_MODEL),
                    ___conditional_do_func(
                        llama_server_process.is_loaded and hasattr(self, "agent"),
                        _remove
                    )
                )
            )
            self.thread_pool.start(llama_worker)

            tool_validator = ToolValidator(self.setting.data)
            agent_worker = Worker(fn=LocasAgent)
            agent_worker.kwargs = {
                "toolset": tool_validator.toolset, 
                "hooks": tool_validator.get_confirmation_strategies_hook(tool_confirmation_ui),
                "port": self.setting.data[SettingKey.LLAMA_PORT],
                "streaming_callback": __enqueue_streaming
            }
            agent_worker.signal.error_signal.connect(
                lambda err: (__chat_message_error(err, None, None),
                             chat_load_button.setEnabled(True))
            )
            agent_worker.signal.result_signal.connect(
                lambda r: (
                    setattr(self, "agent", r),
                    ___conditional_do_func(
                        llama_server_process.is_loaded and hasattr(self, "agent"),
                        _remove
                    )
                )
            )
            self.thread_pool.start(agent_worker)

        else:
            do_func()

    def __docs_add(widget_box: QWidget):
        def ___do():
            layout = widget_box.layout()
            if not isinstance(layout, QBoxLayout):
                return
            layout = layout.itemAt(1)
            if not isinstance(layout, QBoxLayout):
                return

            file_paths, _ = QFileDialog.getOpenFileNames(
                caption = "Select Documents",
                directory = str(PATH.env),
            )

            if not file_paths:
                return

            if not self.agent.docs:
                docs_list_widgets = QListWidget()
                item = ItemButtonDelegate(button_text_callback=lambda _: Constant.BUTTON_DELETE)
                item.button_clicked.connect(lambda m, l=layout, w=widget_box:__docs_remove(m, l, w))
                docs_list_widgets.setItemDelegate(item)
                layout.insertWidget(1, docs_list_widgets)
            else:
                docs_list_widgets = layout.itemAt(1)
                if docs_list_widgets:
                    docs_list_widgets = docs_list_widgets.widget()
                if not isinstance(docs_list_widgets, QListWidget):
                    return
            docs_list_widgets.addItems(file_paths)
            self.agent.docs += file_paths
            LOGGER.info("Add docs: %s", ", ".join(file_paths))
        if self._get(widget_box, UILabel.USER_CHAT_MESSAGE).isReadOnly():
            return
        __set_up_agent(___do)

    def __docs_remove(index: QModelIndex, layout: QBoxLayout, widget_box: QWidget):
        if self._get(widget_box, UILabel.USER_CHAT_MESSAGE).isReadOnly():
            return

        docs_list_widgets = layout.itemAt(1)
        if docs_list_widgets:
            docs_list_widgets = docs_list_widgets.widget()
        if not isinstance(docs_list_widgets, QListWidget):
            return

        item = docs_list_widgets.itemFromIndex(index)
        if item:
            self.agent.docs.pop(docs_list_widgets.row(item))
            docs_list_widgets.takeItem(docs_list_widgets.row(item))

        if not self.agent.docs:
            docs_list_widgets.deleteLater()

    def __chat_message_new():
        user_box = QWidget()
        self._load_ui(UIFiles.CHAT_USER, user_box)
        self._get(user_box, UILabel.USER_CHAT_MESSAGE).keypress_invoke = \
            lambda w=user_box: __chat_message_enter(w)
        self._get(user_box, UILabel.DOCS_BUTTON).clicked.connect(
            lambda _, w=user_box: __docs_add(w)
        )

        chat_scroll_contents.insertWidget(chat_scroll_contents.count() - 1, user_box)

    def __chat_message_error(err: tuple,
                             user_box: QWidget | None,
                             assistant_box: QWidget | None):
        if str(err[1]) == "[Errno 9] Bad file descriptor": # Got when stop generating
            err = (LocasException, "User stops generating.")
        else:
            self._show_error(err)

        if user_box:
            self._get(user_box, UILabel.USER_CHAT_MESSAGE).setReadOnly(False)
        if getattr(self, "agent", None) is None or assistant_box is None:
            return
        assistant_box.deleteLater()
        self.agent.chat_message.append(ChatMessage.from_assistant(
            "An error just occur, I will keep in mind and continue the conversation.\n"
            f"{str(err[0].__name__)}: {str(err[1])}" # type: ignore
        ))
        for widget in (chat_history_box, chat_load_button, docs_load_button):
            widget.setEnabled(True)
        stop_generation_button.setEnabled(False)

    def __chat_message_result(final_output: str):
        LOGGER.info("Assistant: %s", final_output)
        self.current_assistant_box.setMarkdown(final_output)
        self.agent.docs = []

        if chat_history_box.currentIndex() > 0:
            _filename: str = self.agent.chat_to_history(chat_history_box.currentText())
            __chat_message_new()
            _, file_name = os.path.split(_filename)
        else:
            _filename: str = self.agent.chat_to_history()
            __history_setup()
            _, file_name = os.path.split(_filename)
            chat_history_box.setCurrentText(file_name)

        files: list[Path] = []
        for file in PATH.histories.iterdir():
            if file.is_file():
                files.append(file)

        files = sorted(files, key = lambda file: file.name)
        while len(files) > self.setting.data.get(SettingKey.MAX_HISTORY,
                                                 Constant.DEFAULT_MAX_HISTORY):
            for file in files:
                if file.exists() and file.name != file_name:
                    files.remove(file)
                    file.unlink()
                    break
            __history_setup()
            chat_history_box.setCurrentText(file_name)
        for widget in (chat_history_box, chat_load_button, docs_load_button):
            widget.setEnabled(True)
        stop_generation_button.setEnabled(False)

    def __chat_streaming(chunk: StreamingChunk):
        if chunk.start:
            self.current_assistant_message += Constant.MESSAGE_LINE_BREAK
        if chunk.content:
            self.current_assistant_message += chunk.content
        elif chunk.reasoning:
            self.current_assistant_message += chunk.reasoning.reasoning_text
        elif chunk.tool_calls:
            tool_call = chunk.tool_calls[0]
            if tool_call.tool_name:
                self.current_assistant_message += f"**TOOL CALL:** {tool_call.tool_name}"
            if tool_call.arguments:
                self.current_assistant_message += tool_call.arguments
        elif chunk.tool_call_result:
            LOGGER.info("TOOL CALL: %s", chunk.tool_call_result.origin)

            result = chunk.tool_call_result.result
            LOGGER.info("TOOL RESULT: %s", result)

            if len(result) > Constant.TOOL_RESULT_LENGTH_LIMIT:
                result = f"{result[:Constant.TOOL_RESULT_LENGTH_LIMIT]}..."
            self.current_assistant_message += f"**TOOL RESULT:** {result}"

        self.current_assistant_box.setMarkdown(self.current_assistant_message)

    @pyqtSlot()
    def __flush_streaming():
        while True:
            try:
                chunk = streaming_queue.get_nowait()
            except queue.Empty:
                break
            __chat_streaming(chunk)

    def __enqueue_streaming(chunk: StreamingChunk):
        streaming_queue.put(chunk)
        streaming_dispatcher.flush.emit()

    def __chat_message_enter(widget_box: QWidget):
        for widget in (chat_history_box, chat_load_button, docs_load_button):
            widget.setEnabled(False)

        def ___do():
            stop_generation_button.setEnabled(True)
            if chat_history_box.currentIndex() == 0:
                self.agent.chat_message = [ChatMessage.from_system(system_message.toPlainText() + \
                                           Constant.REQUIRED_SYSTEM_MESSAGE)]

            user_docs: dict = LocasDocs.analyze_docs(self.agent.docs)
            user_text = self._get(widget_box, UILabel.USER_CHAT_MESSAGE).toPlainText()

            if hasattr(self, "docs"):
                global_docs: dict = self.docs.retrieve_for_chat(user_text)
                user_docs["documents"] += global_docs.get("documents", [])
                user_docs["images"] += global_docs.get("images", [])

            user_text = self.agent.builder.run(template_variables = {
                "query": user_text,
                "emotion": "None", #TODO
                "documents": user_docs.get("documents", [])
            }).get("prompt", "")

            if not user_text:
                user_text = "The query is empty."
            self.agent.chat_message.append(ChatMessage.from_user(
                content_parts=[user_text, *ImageFileToImageContent().run(
                    sources=user_docs.get("images", [])
                ).get("image_contents", [])]
            ))

            unclassified: list[str] = list(map(str, user_docs.get("unclassified", [])))
            if unclassified:
                msg: str = f"Unable to read docs: {"\n- ".join(unclassified)}"
                self._show_error((OSError, msg))
                LOGGER.info(msg)
            LOGGER.info("User: %s", user_text)

            assistant_box = QWidget()
            self._load_ui(UIFiles.CHAT_ASSISTANT, assistant_box)
            chat_scroll_contents.insertWidget(chat_scroll_contents.count() - 1, assistant_box)
            self.current_assistant_message = ""
            self.current_assistant_box = self._get(assistant_box, UILabel.ASSISTANT_CHAT_MESSAGE)
            worker = Worker(
                fn=self.agent.agent_chat,
                max_chat_message=self.setting.data.get(
                    SettingKey.MAX_CHAT_MESSAGE, Constant.DEFAULT_MAX_CHAT_MESSAGE
                )
            )
            worker.signal.error_signal.connect(
                lambda err, w0=widget_box, w1=assistant_box: __chat_message_error(err, w0, w1)
            )
            worker.signal.result_signal.connect(__chat_message_result)
            self.thread_pool.start(worker)
        __set_up_agent(___do)

    def __scroll_to_bottom(max_val):
        scrollbar = chat_scroll_area.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(max_val)

    def __history_combobox_is_starred_router(index: QModelIndex) -> bool | None:
        if not index.isValid():
            return None
        model = index.model()
        if isinstance(model, QStandardItemModel):
            history: str = model.itemData(index).get(0, "")
            if history and history != Constant.NEW_HISTORY:
                if history.startswith(Constant.STAR_FORMAT.format(history_file="")):
                    return True
                else:
                    return False
        return None

    def __history_combobox_starred(index: QModelIndex):
        current_history: str = chat_history_box.currentText()

        router = __history_combobox_is_starred_router(index)
        model = index.model()
        if router is None or not isinstance(model, QStandardItemModel):
            return
        old_history: str = model.itemData(index).get(0, "")
        if router: # is starred
            new_history = old_history.removeprefix(Constant.STAR_FORMAT.format(history_file=""))
            shutil.move(
                Constant.STARRED_DIR / new_history,
                PATH.histories / new_history
            )
        else:
            shutil.move(
                PATH.histories / old_history,
                Constant.STARRED_DIR / old_history
            )
            new_history = Constant.STAR_FORMAT.format(history_file=old_history)

        __history_setup()
        if current_history == old_history:
            current_history = new_history
        chat_history_box.currentIndexChanged.disconnect(__history_change)
        chat_history_box.setCurrentText(current_history)
        chat_history_box.currentIndexChanged.connect(__history_change)

    def __history_combobox_button_text(index: QModelIndex) -> str:
        router = __history_combobox_is_starred_router(index)
        if router is None:
            return ""
        if router: # is starred
            return Constant.UNSTAR
        else:
            return Constant.STAR

    def __history_setup():
        chat_history_box.clear()
        histories: list[str] = [Constant.NEW_HISTORY]
        for history_file in PATH.histories.iterdir():
            if history_file.name.endswith(".json"):
                histories.append(history_file.name)

        Constant.STARRED_DIR.mkdir(parents=True, exist_ok=True)
        for history_file in Constant.STARRED_DIR.iterdir():
            if history_file.name.endswith(".json"):
                histories.append(Constant.STAR_FORMAT.format(history_file=history_file.name))

        chat_history_box.addItems(histories)

    def __history_change():
        def ___extract_query_from_user_message(user_text: str) -> str:
            match = re.search(r"Query:\s*(?P<query>.*?)\s*Response:",
                              user_text, flags=re.DOTALL)
            if not match:
                return user_text.strip()
            return match.group("query").strip()

        def ___do():
            for i in reversed(range(1, chat_scroll_contents.count() - 1)):
                item = chat_scroll_contents.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
            if chat_history_box.currentIndex() > 0:
                system_message.setEnabled(False)

                current_history: str = chat_history_box.currentText()
                starred_format: str = Constant.STAR_FORMAT.format(history_file="")
                if current_history.startswith(starred_format):
                    self.agent.history_to_chat(current_history.removeprefix(starred_format), True)
                else:
                    self.agent.history_to_chat(current_history)
            else:
                system_message.setEnabled(True)
                self.agent.chat_message = []
            for chat_message in self.agent.chat_message:
                widget_box = QWidget()
                match chat_message.role:
                    case ChatRole.SYSTEM | ChatRole.TOOL:
                        continue
                    case ChatRole.USER:
                        self._load_ui(UIFiles.CHAT_USER, widget_box)
                        message_box = self._get(widget_box, UILabel.USER_CHAT_MESSAGE)
                        message_box.setReadOnly(True)

                        chat_message_text: str | list = chat_message.text
                        if isinstance(chat_message_text, list):
                            for content in chat_message_text:
                                if content.get("type", "") == "text":
                                    chat_message_text = content.get("text", "")
                                    break
                            if chat_message_text == Constant.TOOL_HOOK_IMAGE_TEXT:
                                continue

                        if isinstance(chat_message_text, str):
                            message_box.setMarkdown(
                                ___extract_query_from_user_message(chat_message_text)
                            )
                    case ChatRole.ASSISTANT:
                        if chat_message.tool_call: # Is tool call.
                            continue
                        self._load_ui(UIFiles.CHAT_ASSISTANT, widget_box)
                        self._get(widget_box, UILabel.ASSISTANT_CHAT_MESSAGE).setMarkdown(
                            chat_message.text
                        )
                chat_scroll_contents.insertWidget(chat_scroll_contents.count() - 1, widget_box)
            __chat_message_new()
            chat_load_button.setEnabled(True)

        __set_up_agent(___do)

    def __load_or_unload_agent():
        if hasattr(self, "agent"):
            del self.agent

            llama_server = None
            for process in self.processes:
                if isinstance(process, LlamaCppServer):
                    llama_server = process
                    break
            if llama_server:
                llama_server.kill_process_by_port(llama_server.port)

            chat_load_button.setText(Constant.BUTTON_LOAD_MODEL)
        else:
            __set_up_agent(lambda: chat_load_button.setEnabled(True))

    def __chat_stop_generation():
        if hasattr(self, "agent"):
            self.agent.close()
            self.agent.warm_up()

    tool_confirmation_ui = QtHumanInTheLoop(self)

    chat_scroll_area: QScrollArea = self._get(self, UILabel.CHAT_SCROLL_AREA)
    chat_scroll_contents: QBoxLayout = self._get(self, UILabel.CHAT_SCROLL_CONTENTS).layout()
    chat_history_box: QComboBox = self._get(self, UILabel.CHAT_HISTORY)
    reset_button: QPushButton = self._get(self, UILabel.RESET_BUTTON)
    system_message: QPlainTextEdit = self._get(self, UILabel.SYSTEM_CHAT_MESSAGE)
    stop_generation_button: QPushButton = self._get(self, UILabel.STEP_GENERATION_BUTTON)
    chat_load_button: QPushButton = self._get(self, UILabel.CHAT_LOAD_BUTTON)
    docs_load_button: QPushButton = self._get(self, UILabel.DOCS_LOAD_BUTTON)

    __system_setup()
    __history_setup()
    chat_history_box.setCurrentIndex(0)
    chat_history_box.currentIndexChanged.connect(__history_change)

    chat_history_box_delegate = ItemButtonDelegate(
        button_text_callback=__history_combobox_button_text
    )
    chat_history_box_delegate.button_clicked.connect(__history_combobox_starred)
    chat_history_box.setItemDelegate(chat_history_box_delegate)

    reset_button.clicked.connect(__system_setup)
    system_message.dragEnterEvent = __system_drag_enter
    system_message.dropEvent = __system_drop
    chat_scroll_contents.addStretch(1)
    _scrollbar = chat_scroll_area.verticalScrollBar()
    if _scrollbar:
        _scrollbar.rangeChanged.connect(lambda _, val: __scroll_to_bottom(val))
    __chat_message_new()

    chat_load_button.clicked.connect(__load_or_unload_agent)
    stop_generation_button.clicked.connect(__chat_stop_generation)

    streaming_queue: queue.Queue[StreamingChunk] = queue.Queue()
    streaming_dispatcher = StreamingDispatcher(self)
    streaming_dispatcher.flush.connect(__flush_streaming)
