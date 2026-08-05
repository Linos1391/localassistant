#pylint: disable=E0611:no-name-in-module C0103:invalid-name
"""Custom text and button inside Qt Object."""
from typing import Callable

from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QStyle, QStyleOptionButton, QStyleOptionViewItem, QStyledItemDelegate
from PyQt6.QtCore import (QAbstractItemModel, QEvent, QModelIndex, QPoint, QRect,
                          QSortFilterProxyModel, Qt, pyqtSignal)

from localassistant.utils import Constant

class ItemButtonDelegate(QStyledItemDelegate):
    """Button delegate for QFileSystemModel and QStandardItemModel views."""
    button_clicked = pyqtSignal(QModelIndex)

    def __init__(
        self,
        *args,
        button_text_callback: Callable | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.button_text_callback = button_text_callback or (lambda _: "")

        self._mouse_pos: QPoint | None = None
        self._is_pressed = False

    def _source_index(self, index: QModelIndex) -> QModelIndex:
        proxy_model = index.model()
        if isinstance(proxy_model, QSortFilterProxyModel):
            return proxy_model.mapToSource(index)
        return index

    def get_button_text(self, index: QModelIndex) -> str:
        """Get the destined button text."""
        return self.button_text_callback(self._source_index(index))

    def get_option(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Get the button options for the path."""
        if option.widget is None:
            return None

        button_text = self.get_button_text(index)
        if not button_text:
            return None

        button_option = QStyleOptionButton()
        button_option.initFrom(option.widget)
        button_option.text = button_text

        button_option.rect = QRect(option.rect)
        button_option.rect.setLeft(option.rect.right() - Constant.BUTTON_MINIMUM_WIDTH)

        style = option.widget.style()
        if style is None:
            return button_option

        text_rect = style.subElementRect(QStyle.SubElement.SE_PushButtonContents, button_option)
        margin = style.pixelMetric(QStyle.PixelMetric.PM_ButtonMargin, button_option) * 2
        text_width = button_option.fontMetrics.horizontalAdvance(button_option.text)

        if text_rect.width() < text_width + margin:
            button_option.rect.setLeft(
                button_option.rect.left() - (text_width - text_rect.width() + margin)
            )

        return button_option

    def editorEvent(self,
                    event: QEvent | None,
                    model: QAbstractItemModel | None,
                    option: QStyleOptionViewItem,
                    index: QModelIndex) -> bool:
        """Listen to the event and act like a button."""
        button_option = self.get_option(option, index)
        if not isinstance(event, QMouseEvent) or button_option is None:
            return super().editorEvent(event, model, option, index)

        mouse_pos = event.pos()

        match event.type():
            case QEvent.Type.Enter | QEvent.Type.MouseMove:
                self._mouse_pos = mouse_pos
            case QEvent.Type.Leave:
                self._mouse_pos = None
            case QEvent.Type.MouseButtonPress | QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton\
                                            and button_option.rect.contains(mouse_pos):
                    self.button_clicked.emit(index)
                    self._is_pressed = True
                    option.widget.update()
                    return True
            case QEvent.Type.MouseButtonRelease:
                if self._is_pressed and event.button() == Qt.MouseButton.LeftButton\
                                            and button_option.rect.contains(mouse_pos):
                    self._is_pressed = False
                    option.widget.update()
                    return True
        option.widget.update()
        return super().editorEvent(event, model, option, index)

    def paint(self,
              painter: QPainter | None,
              option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        """Paint the item to look like a button."""
        super().paint(painter, option, index)

        button_option = self.get_option(option, index)
        if button_option is None:
            return

        button_option.state &= ~QStyle.StateFlag.State_HasFocus

        if self._mouse_pos is not None and button_option.rect.contains(self._mouse_pos):
            button_option.state |= QStyle.StateFlag.State_MouseOver
            if self._is_pressed:
                button_option.state |= QStyle.StateFlag.State_On
        else:
            button_option.state &= ~QStyle.StateFlag.State_MouseOver

        style = option.widget.style()
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_PushButton, button_option, painter)
