"Worker file for threading purpose."
import sys
import logging

#pylint: disable=E0611:no-name-in-module
from PyQt6.QtCore import QRunnable, pyqtSlot, pyqtSignal, QObject
from localassistant.utils import LocasException

LOGGER = logging.getLogger(__name__)

class WorkerSignal(QObject):
    """The custom signal"""
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(tuple)

    streaming_signal = pyqtSignal(object)

class Worker(QRunnable):
    """Worker for Qt Threading."""
    _active_workers: set["Worker"] = set()

    def __init__(self, fn, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.kwargs = kwargs
        self.signal = WorkerSignal()
        self.setAutoDelete(False)
        self._active_workers.add(self)
        self.signal.result_signal.connect(self._cleanup)
        self.signal.error_signal.connect(self._cleanup)

    def _cleanup(self, *_args) -> None:
        self._active_workers.discard(self)

    @pyqtSlot()
    def run(self) -> None:
        """Run what need to be."""
        if self.fn is None:
            raise LocasException("Invoked worker without declaring used function.")

        try:
            result = self.fn(**self.kwargs)
        except Exception: #pylint:disable=W0718:broad-exception-caught
            err, value = sys.exc_info()[:2]
            LOGGER.exception("Worker failed: fn=%s, err=%s, value=%s", str(self.fn), err, value)
            self.signal.error_signal.emit((err, value))
        else:
            self.signal.result_signal.emit(result)
