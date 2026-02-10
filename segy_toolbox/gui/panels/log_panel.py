"""Change log viewer panel."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import ChangeRecord


class LogPanel(QWidget):
    """Displays timestamped log entries and change records."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._changes: list[ChangeRecord] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Change Log")
        title.setObjectName("sectionLabel")
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("0 entries")
        self._count_label.setObjectName("subtitleLabel")
        header.addWidget(self._count_label)

        layout.addLayout(header)

        # Log text area
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 10))
        self._log_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self._log_text, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_csv = QPushButton("CSV 내보내기")
        btn_csv.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_csv)

        btn_excel = QPushButton("Excel 내보내기")
        btn_excel.setObjectName("primaryButton")
        btn_excel.clicked.connect(self._export_excel)
        btn_row.addWidget(btn_excel)

        btn_clear = QPushButton("로그 지우기")
        btn_clear.setObjectName("dangerButton")
        btn_clear.clicked.connect(self.clear_log)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_log(self, message: str) -> None:
        """Append a timestamped log message."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.appendPlainText(f"[{ts}] {message}")

    def append_change(self, change: ChangeRecord) -> None:
        """Append a change record to the log."""
        self._changes.append(change)
        trace_info = f" (trace {change.trace_index})" if change.trace_index is not None else ""
        msg = (
            f"{change.field_type}/{change.field_name}{trace_info}: "
            f"{change.before_value} -> {change.after_value}"
        )
        self.append_log(msg)
        self._count_label.setText(f"{len(self._changes)} entries")

    def append_changes(self, changes: list[ChangeRecord]) -> None:
        """Append multiple change records."""
        for c in changes:
            self._changes.append(c)

        if changes:
            self.append_log(
                f"--- {len(changes)} changes applied to {changes[0].filename} ---"
            )
            # Show summary, not every individual change
            by_type: dict[str, int] = {}
            for c in changes:
                key = f"{c.field_type}/{c.field_name}"
                by_type[key] = by_type.get(key, 0) + 1
            for key, count in by_type.items():
                self.append_log(f"  {key}: {count} change(s)")

        self._count_label.setText(f"{len(self._changes)} entries")

    def clear_log(self) -> None:
        self._changes.clear()
        self._log_text.clear()
        self._count_label.setText("0 entries")

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._changes:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "CSV 변경 로그 저장", "changelog.csv", "CSV Files (*.csv)"
        )
        if path:
            from segy_toolbox.reporting.changelog import write_changelog_csv
            write_changelog_csv(self._changes, path)
            self.append_log(f"CSV exported: {path}")

    def _export_excel(self) -> None:
        if not self._changes:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Excel 변경 로그 저장", "changelog.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            import pandas as pd
            from dataclasses import asdict

            df = pd.DataFrame([asdict(c) for c in self._changes])
            df.to_excel(path, index=False, engine="openpyxl")
            self.append_log(f"Excel exported: {path}")
