"""Binary file header editor panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.io.reader import BINARY_FIELD_MAP
from segy_toolbox.models import BinaryHeaderEdit, SegyFileInfo


class BinaryPanel(QWidget):
    """Binary file header editor with field-level editing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_values: dict[str, int] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Binary File Header Editor")
        title.setObjectName("sectionLabel")
        header.addWidget(title)
        header.addStretch()

        self._btn_reset = QPushButton("원본 복원")
        self._btn_reset.clicked.connect(self._reset_values)
        header.addWidget(self._btn_reset)

        layout.addLayout(header)

        # Info
        info = QLabel("값을 수정하려면 'New Value' 열을 직접 편집하세요. 수정된 필드는 파란색으로 표시됩니다.")
        info.setObjectName("subtitleLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Field Name", "Byte Offset", "Type", "Current Value", "New Value"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table, stretch=1)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet("color: #f9e2af;")
        layout.addWidget(self._status)

    def load_from_info(self, info: SegyFileInfo) -> None:
        """Populate the table with binary header values."""
        self._original_values = dict(info.binary_header)
        self._populate_table()

    def get_edits(self) -> list[BinaryHeaderEdit]:
        """Collect all modified fields as BinaryHeaderEdit objects."""
        edits: list[BinaryHeaderEdit] = []

        for row in range(self._table.rowCount()):
            field_name = self._table.item(row, 0).text()
            new_item = self._table.item(row, 4)
            if not new_item:
                continue

            new_text = new_item.text().strip()
            if not new_text:
                continue

            original = self._original_values.get(field_name, 0)
            try:
                new_val = int(new_text)
            except ValueError:
                try:
                    new_val = int(float(new_text))
                except ValueError:
                    continue

            if new_val != original:
                dtype_text = self._table.item(row, 2).text()
                edits.append(BinaryHeaderEdit(
                    field_name=field_name,
                    value=new_val,
                    dtype=dtype_text,
                ))

        return edits

    def clear(self) -> None:
        self._original_values = {}
        self._table.setRowCount(0)
        self._status.setText("")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _populate_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(len(BINARY_FIELD_MAP))

        for row, (name, (enum_val, dtype, offset)) in enumerate(BINARY_FIELD_MAP.items()):
            val = self._original_values.get(name, 0)

            # Field name (read-only)
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 0, name_item)

            # Byte offset (read-only)
            offset_item = QTableWidgetItem(str(offset))
            offset_item.setFlags(offset_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 1, offset_item)

            # Data type (read-only)
            dtype_item = QTableWidgetItem(dtype)
            dtype_item.setFlags(dtype_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 2, dtype_item)

            # Current value (read-only)
            current_item = QTableWidgetItem(str(val))
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 3, current_item)

            # New value (editable)
            new_item = QTableWidgetItem(str(val))
            self._table.setItem(row, 4, new_item)

        self._table.blockSignals(False)
        self._update_status()

    def _reset_values(self) -> None:
        self._table.blockSignals(True)
        for row in range(self._table.rowCount()):
            current_item = self._table.item(row, 3)
            new_item = self._table.item(row, 4)
            if current_item and new_item:
                new_item.setText(current_item.text())
                new_item.setBackground(Qt.transparent)
        self._table.blockSignals(False)
        self._update_status()

    def _on_cell_changed(self, row: int, col: int) -> None:
        if col != 4:
            return

        current_item = self._table.item(row, 3)
        new_item = self._table.item(row, 4)
        if not current_item or not new_item:
            return

        if current_item.text() != new_item.text():
            from PySide6.QtGui import QColor
            new_item.setForeground(QColor("#89b4fa"))
        else:
            new_item.setForeground(QColor("#cdd6f4"))

        self._update_status()

    def _update_status(self) -> None:
        edits = self.get_edits()
        if edits:
            self._status.setText(f"{len(edits)} field(s) modified")
        else:
            self._status.setText("")
