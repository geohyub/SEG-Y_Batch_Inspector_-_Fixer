"""File metadata overview panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import FORMAT_NAMES, SegyFileInfo


class OverviewPanel(QWidget):
    """Display file metadata, binary header, and trace header statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(16)

        # Welcome message (shown when no file is loaded)
        self._welcome = QLabel(
            "SEG-Y 파일을 선택하면 메타데이터가 여기에 표시됩니다.\n\n"
            "왼쪽 패널에서 파일을 열거나 폴더를 선택하세요."
        )
        self._welcome.setObjectName("subtitleLabel")
        self._welcome.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._welcome)

        # File info card
        self._info_card = QFrame()
        self._info_card.setObjectName("card")
        self._info_card.setVisible(False)
        info_layout = QVBoxLayout(self._info_card)

        info_title = QLabel("File Information")
        info_title.setObjectName("sectionLabel")
        info_layout.addWidget(info_title)

        self._info_grid = QGridLayout()
        self._info_grid.setSpacing(8)
        info_layout.addLayout(self._info_grid)
        self._layout.addWidget(self._info_card)

        # Binary header table
        self._binary_card = QFrame()
        self._binary_card.setObjectName("card")
        self._binary_card.setVisible(False)
        binary_layout = QVBoxLayout(self._binary_card)

        binary_title = QLabel("Binary File Header")
        binary_title.setObjectName("sectionLabel")
        binary_layout.addWidget(binary_title)

        self._binary_table = QTableWidget()
        self._binary_table.setColumnCount(3)
        self._binary_table.setHorizontalHeaderLabels(["Field", "Value", "Byte Offset"])
        self._binary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._binary_table.verticalHeader().setVisible(False)
        self._binary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        binary_layout.addWidget(self._binary_table)
        self._layout.addWidget(self._binary_card)

        # Trace header statistics table
        self._trace_card = QFrame()
        self._trace_card.setObjectName("card")
        self._trace_card.setVisible(False)
        trace_layout = QVBoxLayout(self._trace_card)

        trace_title = QLabel("Trace Header Statistics")
        trace_title.setObjectName("sectionLabel")
        trace_layout.addWidget(trace_title)

        self._trace_table = QTableWidget()
        self._trace_table.setColumnCount(5)
        self._trace_table.setHorizontalHeaderLabels(
            ["Field", "Min", "Max", "Mean", "Std"]
        )
        self._trace_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._trace_table.verticalHeader().setVisible(False)
        self._trace_table.setEditTriggers(QTableWidget.NoEditTriggers)
        trace_layout.addWidget(self._trace_table)
        self._layout.addWidget(self._trace_card)

        self._layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def update_info(self, info: SegyFileInfo) -> None:
        """Populate the overview with file information."""
        self._welcome.setVisible(False)
        self._info_card.setVisible(True)
        self._binary_card.setVisible(True)
        self._trace_card.setVisible(True)

        # Clear previous info
        while self._info_grid.count():
            item = self._info_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # File info
        fields = [
            ("Filename", info.filename),
            ("File Size", f"{info.file_size_bytes:,} bytes ({info.file_size_bytes / 1024 / 1024:.1f} MB)"),
            ("Trace Count", f"{info.trace_count:,}"),
            ("Samples per Trace", f"{info.samples_per_trace:,}"),
            ("Sample Interval", f"{info.sample_interval} us"),
            ("Data Format", FORMAT_NAMES.get(info.format_code, f"Unknown ({info.format_code})")),
            ("Bytes per Sample", str(info.bytes_per_sample)),
            ("EBCDIC Encoding", info.ebcdic_encoding),
            ("Coordinate Scalar", str(info.coordinate_scalar)),
            ("Expected File Size", f"{info.expected_file_size:,} bytes"),
            (
                "Size Match",
                "MATCH" if info.file_size_bytes == info.expected_file_size else
                f"MISMATCH (diff: {info.file_size_bytes - info.expected_file_size:+,})"
            ),
        ]

        for row, (label_text, value_text) in enumerate(fields):
            label = QLabel(f"{label_text}:")
            label.setStyleSheet("font-weight: 600; color: #a6adc8;")
            value = QLabel(str(value_text))
            self._info_grid.addWidget(label, row, 0)
            self._info_grid.addWidget(value, row, 1)

        # Binary header table
        from segy_toolbox.io.reader import BINARY_FIELD_MAP
        self._binary_table.setRowCount(len(info.binary_header))
        for row, (name, val) in enumerate(info.binary_header.items()):
            self._binary_table.setItem(row, 0, QTableWidgetItem(name))
            self._binary_table.setItem(row, 1, QTableWidgetItem(str(val)))
            offset = BINARY_FIELD_MAP.get(name, (0, "", 0))[2]
            self._binary_table.setItem(row, 2, QTableWidgetItem(str(offset)))

        # Trace header statistics
        stats = info.trace_header_summary
        self._trace_table.setRowCount(len(stats))
        for row, (name, stat) in enumerate(stats.items()):
            self._trace_table.setItem(row, 0, QTableWidgetItem(name))
            self._trace_table.setItem(row, 1, QTableWidgetItem(f"{stat['min']:.0f}"))
            self._trace_table.setItem(row, 2, QTableWidgetItem(f"{stat['max']:.0f}"))
            self._trace_table.setItem(row, 3, QTableWidgetItem(f"{stat['mean']:.1f}"))
            self._trace_table.setItem(row, 4, QTableWidgetItem(f"{stat['std']:.1f}"))

    def clear(self) -> None:
        """Reset to welcome state."""
        self._welcome.setVisible(True)
        self._info_card.setVisible(False)
        self._binary_card.setVisible(False)
        self._trace_card.setVisible(False)
