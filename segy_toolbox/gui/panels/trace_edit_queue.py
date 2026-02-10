"""Edit Queue widget — manages the list of pending trace header edits."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import TraceHeaderEdit


class EditQueueWidget(QWidget):
    """Manages the ordered list of trace header edits to apply."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_queue: list[TraceHeaderEdit] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Edit Queue")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        row = QHBoxLayout()
        self._queue_list = QListWidget()
        row.addWidget(self._queue_list, stretch=1)

        btns = QVBoxLayout()
        self._btn_remove = QPushButton("\uc81c\uac70")
        self._btn_remove.clicked.connect(self._remove_selected)
        btns.addWidget(self._btn_remove)

        self._btn_clear = QPushButton("\uc804\uccb4 \ucd08\uae30\ud654")
        self._btn_clear.setObjectName("dangerButton")
        self._btn_clear.clicked.connect(self._clear_all)
        btns.addWidget(self._btn_clear)
        btns.addStretch()
        row.addLayout(btns)

        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_edit(self, edit: TraceHeaderEdit) -> None:
        self._edit_queue.append(edit)
        self._queue_list.addItem(self._describe(edit))

    def get_edits(self) -> list[TraceHeaderEdit]:
        return list(self._edit_queue)

    def clear(self) -> None:
        self._edit_queue.clear()
        self._queue_list.clear()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _remove_selected(self) -> None:
        row = self._queue_list.currentRow()
        if 0 <= row < len(self._edit_queue):
            self._edit_queue.pop(row)
            self._queue_list.takeItem(row)

    def _clear_all(self) -> None:
        self.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _describe(edit: TraceHeaderEdit) -> str:
        parts = [f"[{edit.mode.upper()}] {edit.field_name}"]
        if edit.mode == "set":
            parts.append(f"= {edit.value}")
        elif edit.mode == "expression":
            parts.append(f"= {edit.expression}")
        elif edit.mode == "copy":
            parts.append(f"\u2190 {edit.source_field}")
        elif edit.mode == "csv_import":
            parts.append(f"\u2190 CSV:{edit.csv_column}")
        if edit.condition:
            parts.append(f"WHERE {edit.condition}")
        return " ".join(parts)
