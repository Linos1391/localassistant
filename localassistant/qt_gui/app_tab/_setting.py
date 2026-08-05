#pylint: disable=E0611:no-name-in-module W0212:protected-access
"""The Setting tab."""
import logging

from PyQt6.QtWidgets import QStyleFactory, QComboBox, QWidget, QLayout, QSizePolicy

from pyqt6_multiselect_combobox import MultiSelectComboBox
from qt_material import apply_stylesheet, list_themes

from localassistant.utils import (ModelGuide, ModelMetadata, UtilsMethod, Constant, SettingKey,
                                  UIFiles)

LOGGER = logging.getLogger(__name__)

class UILabel:
    """Managing ui name tag so that it can be called easier."""
    SETTING_TOKEN = "settingToken"
    DOWNLOAD_TOKEN = "downloadToken"
    SETTING_THEME = "settingTheme"
    SETTING_LLAMA_BIN_PATH = "settingLlamaBinPath"
    SETTING_LLAMA_PORT = "settingLlamaPort"
    SETTING_LLAMA_PORT_KILL = "settingLlamaPortKill"
    SETTING_MAX_CHAT_MESSAGE = "settingMaxChatMessage"
    SETTING_MAX_HISTORY = "settingMaxHistory"
    SETTING_QDRANT_PORT = "settingQdrantPort"
    SETTING_QDRANT_LOAD = "settingQdrantLoad"
    SETTING_TOP_K = "settingTopK"
    SETTING_SCORE_THRESHOLD = "settingScoreThreshold"
    MODEL_ROLE_LABEL = "modelRoleLabel"
    MODEL_COMBO_BOX = "modelComboBox"
    MODEL_GROUP_BOX = "modelGroupBox"
    SAVE_BUTTON = "saveButton"
    CACHE_BUTTON = "cacheButton"

def _setting_tab_setup(self):
    def __setting_setup():
        self._get(self, UILabel.SETTING_TOKEN).setText(
            self.setting.data.setdefault(SettingKey.TOKEN, "")
        )
        self._get(self, UILabel.DOWNLOAD_TOKEN).setText(
            self.setting.data.setdefault(SettingKey.TOKEN, "")
        )
        self._get(self, UILabel.SETTING_THEME).setCurrentText(
            self.setting.data.setdefault(SettingKey.THEME, list_themes()[7])
        )
        apply_stylesheet(self, self.setting.data[SettingKey.THEME],
                         style=QStyleFactory.create("Fusion")) # type: ignore
        apply_stylesheet(self.error_box, self.setting.data[SettingKey.THEME],
                         style=QStyleFactory.create("Fusion")) # type: ignore

        # Chat tab.
        self._get(self, UILabel.SETTING_LLAMA_BIN_PATH).setText(
            self.setting.data.setdefault(SettingKey.LLAMA_CPP_BIN, "")
        )
        self._get(self, UILabel.SETTING_LLAMA_PORT).setText(str(
            self.setting.data.setdefault(SettingKey.LLAMA_PORT, Constant.DEFAULT_LLAMA_PORT)
        ))
        self._get(self, UILabel.SETTING_LLAMA_PORT_KILL).setChecked(
            self.setting.data.setdefault(SettingKey.LLAMA_PORT_KILL, False)
        )
        self._get(self, UILabel.SETTING_MAX_CHAT_MESSAGE).setValue(
            self.setting.data.setdefault(SettingKey.MAX_CHAT_MESSAGE,
                                         Constant.DEFAULT_MAX_CHAT_MESSAGE)
        )
        self._get(self, UILabel.SETTING_MAX_HISTORY).setValue(
            self.setting.data.setdefault(SettingKey.MAX_HISTORY, Constant.DEFAULT_MAX_HISTORY)
        )

        # Documents tab.
        self._get(self, UILabel.SETTING_QDRANT_PORT).setText(str(
            self.setting.data.setdefault(SettingKey.QDRANT_PORT, Constant.DEFAULT_QDRANT_PORT)
        ))
        self._get(self, UILabel.SETTING_QDRANT_LOAD).setChecked(
            self.setting.data.setdefault(SettingKey.QDRANT_LOAD, False)
        )
        self._get(self, UILabel.SETTING_TOP_K).setValue(
            self.setting.data.setdefault(SettingKey.TOP_K, Constant.DEFAULT_TOP_K)
        )
        self._get(self, UILabel.SETTING_SCORE_THRESHOLD).setValue(
            self.setting.data.setdefault(SettingKey.SCORE_THRESHOLD,
                                         Constant.DEFAULT_SCORE_THRESHOLD)
        )

        # Models tab.
        self.setting.data.setdefault(SettingKey.MODELS, {})
        if setting_model_groupbox:
            while setting_model_groupbox.count():
                item = setting_model_groupbox.takeAt(0)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

        for _model_enum in ModelGuide:
            model_meta: ModelMetadata = _model_enum.value

            model_list: list[str] = model_meta.get_models()

            for role in model_meta.role:
                widget_box = QWidget()
                self._load_ui(UIFiles.SETTING_MODEL, widget_box)
                self._get(widget_box, UILabel.MODEL_ROLE_LABEL).setText(
                    f"<a href='{model_meta.url}'><strong>{UtilsMethod.set_upper(role)}</strong></a>"
                )

                widget_layout = widget_box.layout()
                if not widget_layout:
                    continue

                if model_meta.is_multiple_combobox:
                    combo_box = MultiSelectComboBox()
                else:
                    combo_box = QComboBox()
                combo_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                widget_layout.addWidget(combo_box)

                combo_box.addItems([""] + model_list)
                setting_model_groupbox.addWidget(widget_box) #type:ignore

                self.setting_model_combo_box.update({role: combo_box})
                if model_list:
                    model_id = self.setting.data[SettingKey.MODELS].setdefault(role, "")
                    if model_id not in model_list:
                        model_id = self.setting.data[SettingKey.MODELS][role] = ""
                    combo_box.setCurrentText(model_id)
        self.setting.update_setting_file()

    def __setting_save():
        setting_models: dict = {} # A safe boat for future update. (I broke the app once so.....)
        for role in self.setting.data[SettingKey.MODELS]:
            model_combo_box = self.setting_model_combo_box.get(role)
            if model_combo_box:
                setting_models.update({role: model_combo_box.currentText()})

        self.setting.data.update({
            SettingKey.TOKEN: self._get(self, UILabel.SETTING_TOKEN).text(),
            SettingKey.THEME: setting_theme.currentText(),
            SettingKey.LLAMA_CPP_BIN: self._get(self, UILabel.SETTING_LLAMA_BIN_PATH).text(),
            SettingKey.LLAMA_PORT: int(self._get(self, UILabel.SETTING_LLAMA_PORT).text()),
            SettingKey.LLAMA_PORT_KILL: self._get(self,UILabel.SETTING_LLAMA_PORT_KILL).isChecked(),
            SettingKey.MAX_CHAT_MESSAGE: self._get(self, UILabel.SETTING_MAX_CHAT_MESSAGE).value(),
            SettingKey.MAX_HISTORY: self._get(self, UILabel.SETTING_MAX_HISTORY).value(),
            SettingKey.QDRANT_PORT: int(self._get(self, UILabel.SETTING_QDRANT_PORT).text()),
            SettingKey.QDRANT_LOAD: self._get(self,UILabel.SETTING_QDRANT_LOAD).isChecked(),
            SettingKey.TOP_K: self._get(self, UILabel.SETTING_TOP_K).value(),
            SettingKey.SCORE_THRESHOLD: self._get(self, UILabel.SETTING_SCORE_THRESHOLD).value(),
            SettingKey.MODELS: setting_models,
        })
        __setting_setup()
        self.setting.update_setting_file()
        LOGGER.debug("Sync settings UI")

    setting_model_groupbox: QLayout = self._get(self, UILabel.MODEL_GROUP_BOX).layout()
    if self.setting_model_combo_box: # Already called once, that mean they need the pure setup.
        __setting_setup()
        return

    setting_theme: QComboBox = self._get(self, UILabel.SETTING_THEME)
    setting_theme.addItems(list_themes())
    __setting_setup()
    self._get(self, UILabel.SAVE_BUTTON).clicked.connect(__setting_save)
    self._get(self, UILabel.CACHE_BUTTON).clicked.connect(UtilsMethod.delete_cache)
