#pylint: disable=E0611:no-name-in-module
"""GUI using PyQt."""
import sys
import os
import logging
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import QApplication, QWidget, QDialog, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import QThreadPool, QProcess
from PyQt6.uic import load_ui

from localassistant.utils import LocasException, UIFiles, Constant, SettingKey, Setting, PATH
from localassistant.models.chat import LocasAgent
from localassistant.models.docs import LocasDocs
from localassistant.qt_gui.message_text import MessageTextEdit

LOGGER = logging.getLogger(__name__)

class UILabel:
    """Managing ui name tag so that it can be called easier."""
    CLOSED_BUTTON = "closeButton"
    ERROR_TYPE = "errorType"
    ERROR_INFO = "errorInfo"
    TAB_WIDGETS = "tabWidgets"

class LocasApp(QWidget):
    """The main app."""
    #pylint:disable=C0415:import-outside-toplevel
    from localassistant.qt_gui.app_tab._chat import _chat_tab_setup
    from localassistant.qt_gui.app_tab._docs import _documents_tab_setup
    from localassistant.qt_gui.app_tab._download import _download_tab_setup
    from localassistant.qt_gui.app_tab._setting import _setting_tab_setup

    def __init__(self):
        super().__init__()

        LOGGER.debug("App started")
        self._load_ui(UIFiles.APP, self)

        self.error_box = QDialog()
        self._load_ui(UIFiles.ERROR, self.error_box)
        self._get(self.error_box, UILabel.CLOSED_BUTTON).clicked.connect(self.error_box.hide)
        self.current_assistant_message: str = ""
        self.current_assistant_box: MessageTextEdit

        self.agent: LocasAgent
        self.docs: LocasDocs

        self.processes: list = []
        self.thread_pool = QThreadPool()
        self.setting = Setting()
        self.setting_model_combo_box: dict = {}

        # NOTICE: Download tab will set up setting tab by default
        #self._setting_tab_setup()
        self._chat_tab_setup()
        self._documents_tab_setup()
        self._download_tab_setup()

        self.show()

    @staticmethod
    def _load_ui(ui_file: str, target: Any):
        path: Path = Path(__file__).parent / "ui_file" / ui_file
        LOGGER.debug("Load UI: '%s' for %s", ui_file, target)
        if not path.exists():
            raise LocasException(f"Error loading `.ui` file `{ui_file}` from {path}.")
        load_ui.loadUi(path, target)

    def _show_error(self, error: tuple):
        LOGGER.error("Show error: %s", error[1])
        self._get(self.error_box, UILabel.ERROR_TYPE).setText(str(error[0].__name__))
        self._get(self.error_box, UILabel.ERROR_INFO).setPlainText(str(error[1]))
        self.error_box.show()

    def _show_notify(self, message: str):
        LOGGER.info("Show notification: %s", message)
        tab_widget: QVBoxLayout = self._get(self, UILabel.TAB_WIDGETS).currentWidget().layout()
        if tab_widget is None:
            return

        alert = QLabel(message)
        alert.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        alert.setWordWrap(True)
        alert.setStyleSheet("border: 3px solid #EE4B2B; padding: 10px;")
        tab_widget.insertWidget(0, alert)

        return alert.deleteLater

    @staticmethod
    def _get(parent: Any, widget_name: str) -> Any:
        try:
            return getattr(parent, widget_name)
        except AttributeError as err:
            raise LocasException("Have some issues with `.ui` file. Try to reinstall.") from err

    def _get_model_name(self, role: str, url: str, show_error: bool = True) -> str:
        model_name: str = self.setting.data[SettingKey.MODELS].get(role, "")
        if not model_name and show_error:
            self._show_error((
                LocasException,
                f"No available agent model found. Download one from: '{url}'"
            ))
        return model_name

    @staticmethod
    def _direct_to_model_name(tags: list[str], model: str) -> str:
        if model:
            if not Constant.UNCLASSIFIED in tags:
                tags.append(Constant.UNCLASSIFIED)
            for tag in tags:
                path = PATH.models / tag / model
                if path.exists():
                    return str(path)
        return ""

    def closeEvent(self, a0: QCloseEvent|None): #pylint:disable=C0103:invalid-name
        """Terminate background work and exit the app cleanly."""
        for process in self.processes:
            if process is not None and process.state() == QProcess.ProcessState.Running:
                process.kill()
                process.waitForFinished()

        if self.thread_pool is not None:
            self.thread_pool.clear()
            self.thread_pool.waitForDone(1000)

        # llama.cpp sometimes doesn't shutdown good.
        app = QApplication.instance()
        if app is not None:
            app.quit()

        if a0 is not None:
            a0.accept()

        LOGGER.info("Got shutdown peacefully.")
        os._exit(0)

def main():
    """The app ignition."""
    current_dir = Path.cwd()
    os.chdir(Path(__file__).parent)

    _app = QApplication(sys.argv)
    window = LocasApp() #pylint:disable=W0612:unused-variable
    exit_code: int = _app.exec()

    os.chdir(current_dir)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
