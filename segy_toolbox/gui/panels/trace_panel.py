"""Trace header batch editor panel — composed of sub-widgets.

This is a thin orchestrator that wires together:
- :class:`FieldInspectorWidget` (left — trace header statistics)
- :class:`EditBuilderWidget` (right-top — build a single edit)
- :class:`EditQueueWidget` (right-bottom — list of pending edits)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from segy_toolbox.core.trace_editor import TraceHeaderEditor
from segy_toolbox.gui.panels.trace_edit_builder import EditBuilderWidget
from segy_toolbox.gui.panels.trace_edit_queue import EditQueueWidget
from segy_toolbox.gui.panels.trace_field_inspector import (
    CLICK_SOURCE,
    CLICK_TARGET,
    FieldInspectorWidget,
)
from segy_toolbox.models import SegyFileInfo, TraceHeaderEdit


class TracePanel(QWidget):
    """Trace header batch editor with field inspector and live preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: SegyFileInfo | None = None
        self._build_ui()

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        main_splitter = QSplitter(Qt.Horizontal)

        # [A] Field Inspector (left)
        self._inspector = FieldInspectorWidget()
        self._inspector.field_clicked.connect(self._on_field_clicked)
        main_splitter.addWidget(self._inspector)

        # Right side: vertical splitter
        right_splitter = QSplitter(Qt.Vertical)

        # [B] Edit Builder (right-top)
        self._builder = EditBuilderWidget()
        self._builder.add_button.clicked.connect(self._add_to_queue)
        right_splitter.addWidget(self._builder)

        # [C] Edit Queue (right-bottom)
        self._queue = EditQueueWidget()
        right_splitter.addWidget(self._queue)

        right_splitter.setStretchFactor(0, 7)
        right_splitter.setStretchFactor(1, 3)

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 38)
        main_splitter.setStretchFactor(1, 62)

        layout.addWidget(main_splitter)

    # ==================================================================
    # Public API
    # ==================================================================

    def load_from_info(self, info: SegyFileInfo) -> None:
        """Populate the Field Inspector table from file metadata."""
        self._info = info
        self._inspector.populate(info)
        self._builder.set_file_info(info)

    def get_edits(self) -> list[TraceHeaderEdit]:
        """Return all edits in the queue."""
        return self._queue.get_edits()

    def clear(self) -> None:
        self._queue.clear()
        self._builder.clear()

    # ==================================================================
    # Internal
    # ==================================================================

    def _on_field_clicked(self, field_name: str, click_mode: int) -> None:
        if click_mode == CLICK_TARGET:
            self._builder.set_target_field(field_name)
            self._builder.msg_label.setStyleSheet("color: #89b4fa;")
            self._builder.msg_label.setText(f"Target Field \uc124\uc815: {field_name}")
        else:
            self._builder.set_source_field(field_name)
            self._builder.msg_label.setStyleSheet("color: #f9e2af;")
            self._builder.msg_label.setText(f"Source Field \uc124\uc815: {field_name}")

    def _add_to_queue(self) -> None:
        edit = self._builder.build_edit()
        if edit is None:
            return

        editor = TraceHeaderEditor()
        err = editor.validate_edit(edit)
        if err:
            self._builder.msg_label.setStyleSheet("color: #f38ba8;")
            self._builder.msg_label.setText(f"Error: {err}")
            return

        self._queue.add_edit(edit)
        self._builder.msg_label.setStyleSheet("color: #a6e3a1;")
        self._builder.msg_label.setText("Added to queue")
