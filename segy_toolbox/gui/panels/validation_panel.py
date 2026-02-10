"""Validation results display panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import ValidationCheck, ValidationResult

_STATUS_STYLES = {
    "PASS": ("statusPass", "PASS"),
    "FAIL": ("statusFail", "FAIL"),
    "WARNING": ("statusWarning", "WARNING"),
}

_STATUS_COLORS = {
    "PASS": "#a6e3a1",
    "FAIL": "#f38ba8",
    "WARNING": "#f9e2af",
}


class ValidationPanel(QWidget):
    """Display validation results with status indicators."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: ValidationResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(12)

        # Status header
        self._status_label = QLabel("검증을 실행하세요")
        self._status_label.setObjectName("titleLabel")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._content_layout.addWidget(self._status_label)

        # Summary
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("subtitleLabel")
        self._summary_label.setAlignment(Qt.AlignCenter)
        self._content_layout.addWidget(self._summary_label)

        # Checks container
        self._checks_container = QVBoxLayout()
        self._checks_container.setSpacing(8)
        self._content_layout.addLayout(self._checks_container)

        self._content_layout.addStretch()

        # Export button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._export_btn = QPushButton("검증 리포트 내보내기 (Excel)")
        self._export_btn.setObjectName("primaryButton")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_report)
        btn_layout.addWidget(self._export_btn)
        self._content_layout.addLayout(btn_layout)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def update_result(self, result: ValidationResult) -> None:
        """Display validation results."""
        self._result = result

        # Update status label
        obj_name, text = _STATUS_STYLES.get(
            result.overall_status, ("subtitleLabel", result.overall_status)
        )
        self._status_label.setText(text)
        self._status_label.setObjectName(obj_name)
        self._status_label.setStyleSheet(
            f"color: {_STATUS_COLORS.get(result.overall_status, '#cdd6f4')}; "
            f"font-size: 28px; font-weight: 700;"
        )

        # Summary
        n_pass = sum(1 for c in result.checks if c.status == "PASS")
        n_fail = sum(1 for c in result.checks if c.status == "FAIL")
        n_warn = sum(1 for c in result.checks if c.status == "WARNING")
        self._summary_label.setText(
            f"PASS: {n_pass}  |  FAIL: {n_fail}  |  WARNING: {n_warn}  |  "
            f"Total: {len(result.checks)}"
        )

        # Clear previous checks
        while self._checks_container.count():
            item = self._checks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add check cards
        for check in result.checks:
            card = self._create_check_card(check)
            self._checks_container.addWidget(card)

        self._export_btn.setEnabled(True)

    def clear(self) -> None:
        self._result = None
        self._status_label.setText("검증을 실행하세요")
        self._status_label.setObjectName("titleLabel")
        self._status_label.setStyleSheet("")
        self._summary_label.setText("")
        self._export_btn.setEnabled(False)

        while self._checks_container.count():
            item = self._checks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _create_check_card(self, check: ValidationCheck) -> QFrame:
        """Create a card widget for a single validation check."""
        card = QFrame()
        card.setObjectName("card")

        color = _STATUS_COLORS.get(check.status, "#cdd6f4")
        card.setStyleSheet(
            f"QFrame#card {{ border-left: 4px solid {color}; }}"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header row: status dot + name + category badge
        header = QHBoxLayout()
        status_dot = QLabel(f"  {check.status}")
        status_dot.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 12px;")
        header.addWidget(status_dot)

        name_label = QLabel(check.name)
        name_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        header.addWidget(name_label)

        category = QLabel(check.category)
        category.setStyleSheet(
            "color: #a6adc8; font-size: 11px; padding: 2px 8px; "
            "background: #313244; border-radius: 4px;"
        )
        header.addWidget(category)
        header.addStretch()
        layout.addLayout(header)

        # Message
        msg = QLabel(check.message)
        msg.setStyleSheet("color: #bac2de; font-size: 12px;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Details (if any)
        if check.details:
            details = QLabel(check.details)
            details.setStyleSheet(
                "color: #7f849c; font-size: 11px; "
                "font-family: Consolas, monospace;"
            )
            details.setWordWrap(True)
            layout.addWidget(details)

        return card

    def _export_report(self) -> None:
        if not self._result:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "검증 리포트 저장",
            f"{self._result.filename}_validation.xlsx",
            "Excel Files (*.xlsx)",
        )
        if path:
            from segy_toolbox.models import BatchResult
            from segy_toolbox.reporting.excel_report import write_validation_report

            batch = BatchResult(
                filename=self._result.filename,
                status=self._result.overall_status,
                message=f"{len(self._result.checks)} checks",
                validation_before=self._result,
            )
            write_validation_report([batch], path)
