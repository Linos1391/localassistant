#pylint: disable=E0611:no-name-in-module W0212:protected-access
"""The Download tab."""
import os
from pathlib import Path
import shutil

from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QPushButton, QLineEdit, QTreeView
from PyQt6.QtCore import QDir, QModelIndex, QSortFilterProxyModel

from localassistant.utils import ModelMetadata, Constant, PATH, LOGGER
from localassistant.qt_gui.worker import Worker
from localassistant.qt_gui.item_button_delegate import ItemButtonDelegate

class UILabel:
    """Managing ui name tag so that it can be called easier."""
    DOWNLOAD_TREEVIEW = "downloadTreeview"
    DOWNLOAD_REPO = "downloadRepo"
    DOWNLOAD_BUTTON = "downloadButton"
    DOWNLOAD_TOKEN = "downloadToken"

def _download_tab_setup(self):
    def __download_remove(
        index: QModelIndex,
        proxy_model: QSortFilterProxyModel,
        model: QFileSystemModel
    ):
        source_index = proxy_model.mapToSource(index)
        remove_path: Path = Path(model.filePath(source_index))
        try:
            shutil.rmtree(remove_path)
        except NotADirectoryError:
            remove_path.unlink()

        try:
            os.removedirs(remove_path.parent)
        except OSError:
            pass

        self._setting_tab_setup()

    def __download_setup():
        def ___download_button_text_for_index(index: QModelIndex) -> str:
            if not index.isValid():
                return ""
            model = index.model()
            if isinstance(model, QFileSystemModel):
                relative_parent_path: Path = Path(model.filePath(index)).relative_to(PATH.models)
                if len(relative_parent_path.parents) < 2:
                    return ""
                pipeline_tag: str = str(relative_parent_path.parents[-2])
                relative_path: str = str(relative_parent_path.relative_to(pipeline_tag))

                if relative_path in ModelMetadata.tag_to_models(pipeline_tag):
                    return Constant.BUTTON_DELETE_ALL
                elif not model.isDir(index):
                    return Constant.BUTTON_DELETE
            return ""

        LOGGER.debug("Refresh model list")

        download_model = QFileSystemModel()
        root_index = download_model.setRootPath(str(PATH.models))
        download_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries)
        download_model.setNameFilterDisables(False)
        download_model.setReadOnly(False)
        download_model.fileRenamed.connect(self._setting_tab_setup)

        download_proxy_model = QSortFilterProxyModel()
        download_proxy_model.setSourceModel(download_model)
        download_proxy_model.setRecursiveFilteringEnabled(True)
        download_proxy_model.setFilterRole(QFileSystemModel.Roles.FileNameRole)
        download_proxy_model.setDynamicSortFilter(True)

        download_treeview.setModel(download_proxy_model)
        download_treeview.setRootIndex(download_proxy_model.mapFromSource(root_index))
        download_treeview.hideColumn(1)
        download_treeview.hideColumn(2)
        download_treeview.hideColumn(3)

        download_tree_delegate = ItemButtonDelegate(
            button_text_callback=___download_button_text_for_index
        )
        download_treeview.setItemDelegateForColumn(0, download_tree_delegate)
        download_tree_delegate.button_clicked.connect(
            lambda i, p=download_proxy_model, m=download_model: __download_remove(i, p, m)
        )

        # also update the setting tab
        self._setting_tab_setup()

    def __download():
        download_button.setEnabled(False)
        repo = self._get(self, UILabel.DOWNLOAD_REPO).text().strip()
        LOGGER.info("Download request: %s", repo)

        _remove = self._show_notify(f"Downloading request: {repo}. Please do not interrupt.")

        from localassistant.models.download import download #pylint:disable=C0415:import-outside-toplevel
        worker = Worker(
            fn=download,
            repo_id=repo,
            parent_dir=PATH.models,
            token=download_token.text().strip() if download_token.text().strip() else None
        )
        worker.signal.error_signal.connect(lambda err: (_remove(),
                                                        self._show_error(err),
                                                        download_button.setEnabled(True)))
        worker.signal.result_signal.connect(lambda: (_remove(),
                                                     download_button.setEnabled(True),
                                                     __download_setup(),
                                                     LOGGER.info("Download completed: %s", repo)))
        self.thread_pool.start(worker)

    download_button: QPushButton = self._get(self, UILabel.DOWNLOAD_BUTTON)
    download_token: QLineEdit = self._get(self, UILabel.DOWNLOAD_TOKEN)
    download_treeview: QTreeView = self._get(self, UILabel.DOWNLOAD_TREEVIEW)
    __download_setup()
    download_button.clicked.connect(__download)
