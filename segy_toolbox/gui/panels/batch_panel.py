"""Batch processing controls panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import BatchResult


_STATUS_COLORS = {
    "SUCCESS": "#a6e3a1",
    "FAILURE": "#f38ba8",
    "SKIPPED": "#f9e2af",
}


class BatchPanel(QWidget):
    """Batch processing controls and results display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[BatchResult] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Options card
        options_card = QFrame()
        options_card.setObjectName("card")
        opts = QVBoxLayout(options_card)

        opts_title = QLabel("Batch Options")
        opts_title.setObjectName("sectionLabel")
        opts.addWidget(opts_title)

        # Output mode
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("출력 모드:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("별도 폴더에 저장", "separate_folder")
        self._mode_combo.addItem("원본 위치 (백업 생성)", "in_place_backup")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_combo, stretch=1)
        opts.addLayout(mode_row)

        # Output mode warning/info label
        self._mode_warning = QLabel("")
        self._mode_warning.setWordWrap(True)
        opts.addWidget(self._mode_warning)
        self._on_mode_changed()  # Set initial text

        # Output directory
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("출력 폴더:"))
        self._output_dir = QLineEdit("./output")
        dir_row.addWidget(self._output_dir, stretch=1)
        self._btn_browse = QPushButton("찾아보기")
        self._btn_browse.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(self._btn_browse)
        opts.addLayout(dir_row)

        # Dry run checkbox
        self._dry_run_check = QCheckBox("Dry Run (미리보기만, 실제 수정 없음)")
        opts.addWidget(self._dry_run_check)

        layout.addWidget(options_card)

        # Summary
        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_layout = QVBoxLayout(summary_card)

        self._summary_label = QLabel("배치 작업을 시작하려면 위 옵션을 설정한 후 사이드바의 '수정 적용' 버튼을 클릭하세요.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setObjectName("subtitleLabel")
        summary_layout.addWidget(self._summary_label)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        summary_layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("subtitleLabel")
        self._progress_label.setVisible(False)
        summary_layout.addWidget(self._progress_label)

        layout.addWidget(summary_card)

        # Results table
        results_title = QLabel("Batch Results")
        results_title.setObjectName("sectionLabel")
        layout.addWidget(results_title)

        self._results_table = QTableWidget()
        self._results_table.setColumnCount(5)
        self._results_table.setHorizontalHeaderLabels(
            ["File", "Status", "Changes", "Duration", "Message"]
        )
        self._results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._results_table.verticalHeader().setVisible(False)
        self._results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._results_table, stretch=1)

        # Export button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_export = QPushButton("리포트 내보내기 (Excel)")
        self._btn_export.setObjectName("primaryButton")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_report)
        btn_row.addWidget(self._btn_export)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_output_mode(self) -> str:
        return self._mode_combo.currentData()

    def get_output_dir(self) -> str:
        return self._output_dir.text().strip()

    def is_dry_run(self) -> bool:
        return self._dry_run_check.isChecked()

    def show_progress(self, current: int, total: int) -> None:
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress.setMaximum(total)
        self._progress.setValue(current)
        self._progress_label.setText(f"파일 {current}/{total} 처리 중...")

    def hide_progress(self) -> None:
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)

    def display_results(self, results: list[BatchResult]) -> None:
        """Show batch results in the table."""
        self._results = results
        self._results_table.setRowCount(len(results))

        n_success = 0
        n_fail = 0
        n_skip = 0

        for row, r in enumerate(results):
            # Filename
            self._results_table.setItem(row, 0, QTableWidgetItem(r.filename))

            # Status (colored)
            status_item = QTableWidgetItem(r.status)
            color = _STATUS_COLORS.get(r.status, "#cdd6f4")
            from PySide6.QtGui import QColor
            status_item.setForeground(QColor(color))
            self._results_table.setItem(row, 1, status_item)

            # Changes count
            self._results_table.setItem(row, 2, QTableWidgetItem(str(len(r.changes))))

            # Duration
            self._results_table.setItem(
                row, 3, QTableWidgetItem(f"{r.duration_seconds:.1f}s")
            )

            # Message
            self._results_table.setItem(row, 4, QTableWidgetItem(r.message))

            if r.status == "SUCCESS":
                n_success += 1
            elif r.status == "FAILURE":
                n_fail += 1
            else:
                n_skip += 1

        self._summary_label.setText(
            f"완료: {n_success} 성공, {n_fail} 실패, {n_skip} 건너뜀 "
            f"(총 {len(results)} 파일)"
        )
        self._btn_export.setEnabled(True)
        self.hide_progress()

    def clear(self) -> None:
        self._results = []
        self._results_table.setRowCount(0)
        self._summary_label.setText("배치 작업을 시작하려면 옵션을 설정하세요.")
        self._btn_export.setEnabled(False)
        self.hide_progress()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self) -> None:
        mode = self._mode_combo.currentData()
        if mode == "in_place_backup":
            self._mode_warning.setText(
                "\u26a0 \uc6d0\ubcf8 \ud30c\uc77c\uc774 \uc9c1\uc811 \uc218\uc815\ub429\ub2c8\ub2e4. "
                "\ubc31\uc5c5 \ud30c\uc77c(.bak)\uc774 \uac19\uc740 \uc704\uce58\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4."
            )
            self._mode_warning.setStyleSheet("color: #f38ba8; font-weight: bold;")
        else:
            self._mode_warning.setText(
                "\u2713 \uc6d0\ubcf8 \ud30c\uc77c\uc740 \ubcc0\uacbd\ub418\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. "
                "\ubcf5\uc0ac\ubcf8\uc774 \ucd9c\ub825 \ud3f4\ub354\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4."
            )
            self._mode_warning.setStyleSheet("color: #a6e3a1;")

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if folder:
            self._output_dir.setText(folder)

    def _export_report(self) -> None:
        if not self._results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "배치 리포트 저장",
            "batch_report.xlsx",
            "Excel Files (*.xlsx)",
        )
        if path:
            from segy_toolbox.reporting.excel_report import write_validation_report
            write_validation_report(self._results, path)
