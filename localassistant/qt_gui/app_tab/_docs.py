#pylint: disable=E0611:no-name-in-module W0212:protected-access
"""The Documents tab."""
import logging
from pathlib import Path
from typing import Callable

from haystack import Document

from PyQt6.QtWidgets import QTreeView, QPushButton, QFileDialog
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QModelIndex

from localassistant.models.docs import LocasDocs, EmbeddingMode
from localassistant.qt_gui.worker import Worker
from localassistant.qt_gui.item_button_delegate import ItemButtonDelegate
from localassistant.utils import ModelMetadata, ModelGuide, Constant, SettingKey, PATH

LOGGER = logging.getLogger(__name__)

class UILabel:
    """Managing ui name tag so that it can be called easier."""
    DOCS_TREE_VIEW = "docsTreeView"
    DOCS_ADD_BUTTON = "docsAddButton"
    DOCS_REEMBED_BUTTON = "docsReembedButton"
    DOCS_LOAD_BUTTON = "docsLoadButton"

def _documents_tab_setup(self):
    # from localassistant.qt_gui.app import App
    # self = App() #TODO - cooking
    def __set_up_docs_model(do_func: Callable):
        if getattr(self, "docs", None) is None:
            docs_kwargs: dict = {
                "port": self.setting.data.get(SettingKey.QDRANT_PORT, Constant.DEFAULT_QDRANT_PORT),
                "top_k": self.setting.data.get(SettingKey.TOP_K, Constant.DEFAULT_TOP_K),
                "score_threshold": self.setting.data.get(
                    SettingKey.SCORE_THRESHOLD, Constant.DEFAULT_SCORE_THRESHOLD
                )
            }
            msg = "Load documents model for"
            for embedding_mode in EmbeddingMode:
                model_meta = getattr(ModelGuide, f"DOCS_{embedding_mode.name}").value
                if not isinstance(model_meta, ModelMetadata):
                    continue

                model_repo_id = self._get_model_name(
                    model_meta.role[0], model_meta.url, show_error = False
                )
                model_repo_id = self._direct_to_model_name(model_meta.tag, model_repo_id)
                if not model_repo_id:
                    model_repo_id = None
                else:
                    model_repo_id = Path(model_repo_id)
                    msg += f" {embedding_mode.name}"
                docs_kwargs.update({f"{embedding_mode.name.lower()}_model_path": model_repo_id})

            LOGGER.info(msg)
            _remove = self._show_notify(msg)

            docs_worker = Worker(fn=LocasDocs, **docs_kwargs)
            docs_worker.signal.error_signal.connect(
                lambda err: (self._show_error(err), _remove())
            )
            docs_worker.signal.result_signal.connect(
                lambda r: (
                    setattr(self, "docs", r), _remove(),
                    docs_load_button.setText(Constant.BUTTON_UNLOAD_MODEL),
                    do_func(),
                )
            )
            self.thread_pool.start(docs_worker)

        else:
            do_func()

    def __docs_add():
        def ___do():
            file_paths, _ = QFileDialog.getOpenFileNames(
                caption = "Select Documents",
                directory = str(PATH.env),
            )

            docs_worker = Worker(fn=self.docs.write_docs, docs_paths=file_paths)
            docs_worker.signal.error_signal.connect(self._show_error)
            docs_worker.signal.result_signal.connect(__documents_setup)
            self.thread_pool.start(docs_worker)

        __set_up_docs_model(___do)

    def __docs_reembed():
        def ___do():
            docs_worker = Worker(fn=self.docs.re_embed_all)
            docs_worker.signal.error_signal.connect(self._show_error)
            docs_worker.signal.result_signal.connect(__documents_setup)
            self.thread_pool.start(docs_worker)

        __set_up_docs_model(___do)

    def __docs_remove(index: QModelIndex):
        model = index.model()
        if isinstance(model, QStandardItemModel):
            docs_index = model.item(index.row(), 0)
            if docs_index:
                docs_id_index = docs_index.takeChild(0, 1)
                if docs_id_index:
                    docs_worker = Worker(
                        fn=self.docs.delete_docs,
                        filename=docs_index.text(),
                        doc_id=docs_id_index.text()
                    )
                    docs_worker.signal.error_signal.connect(self._show_error)
                    docs_worker.signal.result_signal.connect(__documents_setup)
                    self.thread_pool.start(docs_worker)

    def __docs_delegate_button_text(index: QModelIndex):
        if index.isValid() and not index.parent().isValid() and index.column() == 1:
            return Constant.BUTTON_DELETE
        return ""

    def __documents_setup():
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Documents", "Property"])

        documents: list[Document] = self.docs.get_all_docs()
        for document in documents:
            if not isinstance(document, Document):
                continue
            docs_item = QStandardItem(document.meta.get("file_path"))
            model.appendRow([docs_item])

            for docs_property in ("id", "content", "embedding", "sparse_embedding"):
                description = getattr(document, docs_property, None)
                if description:
                    item = QStandardItem(docs_property)
                    item_description = QStandardItem(description)
                    docs_item.appendRow([item, item_description])
            docs_meta = document.meta
            docs_meta.pop("file_path")
            if docs_meta:
                meta_item = QStandardItem("meta")
                for (meta_key, meta_value) in docs_meta.items():
                    item = QStandardItem(meta_key)
                    item_description = QStandardItem(meta_value)
                    meta_item.appendRow([item, item_description])
        docs_tree_view.setModel(model)

    def __load_or_unload_docs_model():
        if hasattr(self, "docs"):
            del self.docs
            docs_load_button.setText(Constant.BUTTON_LOAD_MODEL)
            docs_tree_view.setModel(QStandardItemModel())
        else:
            __set_up_docs_model(__documents_setup)

    docs_tree_view: QTreeView = self._get(self, UILabel.DOCS_TREE_VIEW)
    docs_add_button: QPushButton = self._get(self, UILabel.DOCS_ADD_BUTTON)
    docs_reembed_button: QPushButton = self._get(self, UILabel.DOCS_REEMBED_BUTTON)
    docs_load_button: QPushButton = self._get(self, UILabel.DOCS_LOAD_BUTTON)

    docs_delegate = ItemButtonDelegate(
                button_text_callback=__docs_delegate_button_text
            )
    docs_delegate.button_clicked.connect(__docs_remove)
    docs_tree_view.setItemDelegate(docs_delegate)

    docs_add_button.clicked.connect(__docs_add)
    docs_reembed_button.clicked.connect(__docs_reembed)
    docs_load_button.clicked.connect(__load_or_unload_docs_model)

    if self.setting.data.get(SettingKey.QDRANT_LOAD, False):
        __load_or_unload_docs_model()
