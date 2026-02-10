"""Background workers for GUI threading."""

from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Signal, Slot

from segy_toolbox.config import EditConfig
from segy_toolbox.core.engine import SegyEngine
from segy_toolbox.models import BatchResult, EditJob, SegyFileInfo, ValidationResult


class LoadWorker(QObject):
    """Worker to load a SEG-Y file in a background thread."""

    finished = Signal(object)   # SegyFileInfo
    error = Signal(str)

    def __init__(self, engine: SegyEngine, path: str):
        super().__init__()
        self._engine = engine
        self._path = path

    @Slot()
    def run(self) -> None:
        try:
            info = self._engine.load_file(self._path)
            self.finished.emit(info)
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n\n{tb}")


class ValidateWorker(QObject):
    """Worker to validate a SEG-Y file in a background thread."""

    finished = Signal(object)   # ValidationResult
    error = Signal(str)

    def __init__(self, engine: SegyEngine, info: SegyFileInfo):
        super().__init__()
        self._engine = engine
        self._info = info

    @Slot()
    def run(self) -> None:
        try:
            result = self._engine.validate(self._info)
            self.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n\n{tb}")


class ApplyWorker(QObject):
    """Worker to apply edits to a SEG-Y file in a background thread."""

    stage_changed = Signal(int, str)
    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal(str, list, object)  # output_path, changes, post_validation
    error = Signal(str)

    def __init__(self, engine: SegyEngine, path: str, job: EditJob):
        super().__init__()
        self._engine = engine
        self._path = path
        self._job = job

    @Slot()
    def run(self) -> None:
        try:
            self._engine.set_callbacks(
                on_stage=lambda idx, name: self.stage_changed.emit(idx, name),
                on_progress=lambda cur, total: self.progress.emit(cur, total),
                on_log=lambda msg: self.log.emit(msg),
            )
            output_path, changes, post_val = self._engine.apply(self._path, self._job)
            self.finished.emit(output_path, changes, post_val)
        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit(f"ERROR TRACEBACK:\n{tb}")
            self.error.emit(f"{e}\n\n{tb}")


class BatchWorker(QObject):
    """Worker to run batch processing in a background thread."""

    stage_changed = Signal(int, str)
    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal(list)     # list[BatchResult]
    error = Signal(str)

    def __init__(self, engine: SegyEngine, paths: list[str], job: EditJob):
        super().__init__()
        self._engine = engine
        self._paths = paths
        self._job = job

    @Slot()
    def run(self) -> None:
        try:
            self._engine.set_callbacks(
                on_stage=lambda idx, name: self.stage_changed.emit(idx, name),
                on_progress=lambda cur, total: self.progress.emit(cur, total),
                on_log=lambda msg: self.log.emit(msg),
            )
            results = self._engine.run_batch(self._paths, self._job)
            self.finished.emit(results)
        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit(f"ERROR TRACEBACK:\n{tb}")
            self.error.emit(f"{e}\n\n{tb}")


class DryRunWorker(QObject):
    """Worker to perform dry run preview in a background thread."""

    finished = Signal(dict)     # preview results
    error = Signal(str)

    def __init__(self, engine: SegyEngine, path: str, job: EditJob):
        super().__init__()
        self._engine = engine
        self._path = path
        self._job = job

    @Slot()
    def run(self) -> None:
        try:
            result = self._engine.preview(self._path, self._job)
            self.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n\n{tb}")
