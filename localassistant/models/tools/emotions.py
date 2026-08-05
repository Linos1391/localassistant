"""The tools library."""
from typing import Literal
from threading import Thread

from haystack.tools import create_tool_from_function

#pylint: disable=E0611:no-name-in-module
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import pyqtSignal

from animflow import Displayer, Animation

_app = QApplication([])

displayer = Displayer()

for anim in ["disguised", "idle", "love", "surprise"]:
    displayer.add_animation(Animation(f"/home/linos1391/Downloads/lumine/anim/{anim}.tar.xz"))

def get_current_emotion() -> str:
    """Get the current emotion for better expression."""
    return displayer.selected


def set_emotion(emotion: Literal["disguised", "idle", "love", "surprise"]) -> bool:
    """There are four main emotion, choose correctly! Return True if emotion is shown."""
    return displayer.select_animation(emotion, loop=True)

tools = [create_tool_from_function(get_current_emotion),
         create_tool_from_function(set_emotion)]

class ClickableWidget(QWidget):
    # Define a custom signal
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        displayer.select_animation("disguised", loop=True)
        return super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        displayer.select_animation("idle", loop=True)        
        return super().mouseReleaseEvent(a0)

def start():
    displayer.select_animation("idle", loop=True)
    displayer.display(container=ClickableWidget())

start()
