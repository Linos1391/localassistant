"""Custom widget."""
#pylint: disable=E0611:no-name-in-module C0103:invalid-name
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import Qt

class MessageTextEdit(QTextBrowser):
    """Custom widget for auto-resizing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self._auto_resize)

    def _auto_resize(self):
        doc = self.document()
        view = self.viewport()
        if doc is None or view is None:
            return
        doc.setTextWidth(view.width())
        margins = self.contentsMargins()
        height = int(doc.size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, a0):
        """Detect when the event happen."""
        self._auto_resize()
        super().resizeEvent(a0)

    def keypress_invoke(self):
        """For overwrite purpose by the parent widget."""

    def keyPressEvent(self, ev: QKeyEvent | None):
        """To send the text when user enter."""
        if ev is None or self.isReadOnly():
            return
        if ev.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return) and\
                    ev.modifiers().value != Qt.Modifier.SHIFT.value and\
                    self.toPlainText().strip() != "":
            self.setReadOnly(True)
            self.keypress_invoke()
        super().keyPressEvent(ev)
