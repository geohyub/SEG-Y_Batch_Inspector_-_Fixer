"""Main application window for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox import __version__
from segy_toolbox.config import EditConfig
from segy_toolbox.core.engine import SegyEngine
from segy_toolbox.gui.panels.batch_panel import BatchPanel
from segy_toolbox.gui.panels.binary_panel import BinaryPanel
from segy_toolbox.gui.panels.ebcdic_panel import EbcdicPanel
from segy_toolbox.gui.panels.file_panel import FilePanel
from segy_toolbox.gui.panels.log_panel import LogPanel
from segy_toolbox.gui.panels.overview_panel import OverviewPanel
from segy_toolbox.gui.panels.trace_panel import TracePanel
from segy_toolbox.gui.panels.validation_panel import ValidationPanel
from segy_toolbox.gui.workers import (
    ApplyWorker,
    BatchWorker,
    DryRunWorker,
    LoadWorker,
    ValidateWorker,
)
from segy_toolbox.models import EditJob, SegyFileInfo, ValidationResult


class MainWindow(QMainWindow):
    """SEG-Y Batch Inspector & Fixer main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SEG-Y Batch Inspector & Fixer v{__version__}")
        self.setMinimumSize(1200, 800)
        self.resize(1440, 900)

        self._engine = SegyEngine()
        self._current_info: SegyFileInfo | None = None
        self._current_validation: ValidationResult | None = None
        self._worker_thread: QThread | None = None
        self._dry_run_executed: bool = False

        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._apply_theme()

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("파일 열기...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._file_panel_open_file)
        file_menu.addAction(open_action)

        folder_action = QAction("폴더 열기...", self)
        folder_action.setShortcut("Ctrl+Shift+O")
        folder_action.triggered.connect(self._file_panel_open_folder)
        file_menu.addAction(folder_action)

        file_menu.addSeparator()

        exit_action = QAction("종료", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")

        validate_action = QAction("검증 실행", self)
        validate_action.setShortcut("Ctrl+V")
        validate_action.triggered.connect(self._run_validate)
        tools_menu.addAction(validate_action)

        dry_run_action = QAction("Dry Run (미리보기)", self)
        dry_run_action.setShortcut("Ctrl+D")
        dry_run_action.triggered.connect(self._run_dry_run)
        tools_menu.addAction(dry_run_action)

        apply_action = QAction("수정 적용", self)
        apply_action.setShortcut("Ctrl+Return")
        apply_action.triggered.connect(self._run_apply)
        tools_menu.addAction(apply_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left Sidebar ----
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # File panel
        self._file_panel = FilePanel()
        self._file_panel.file_selected.connect(self._on_file_selected)
        sidebar_layout.addWidget(self._file_panel, stretch=1)

        # Action buttons
        actions_frame = QFrame()
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(8, 8, 8, 8)
        actions_layout.setSpacing(6)

        action_title = QLabel("Actions")
        action_title.setObjectName("sectionLabel")
        actions_layout.addWidget(action_title)

        self._btn_validate = QPushButton("검증 실행")
        self._btn_validate.setObjectName("primaryButton")
        self._btn_validate.clicked.connect(self._run_validate)
        self._btn_validate.setEnabled(False)
        actions_layout.addWidget(self._btn_validate)

        self._btn_dry_run = QPushButton("Dry Run (미리보기)")
        self._btn_dry_run.clicked.connect(self._run_dry_run)
        self._btn_dry_run.setEnabled(False)
        actions_layout.addWidget(self._btn_dry_run)

        self._btn_apply = QPushButton("수정 적용")
        self._btn_apply.setObjectName("successButton")
        self._btn_apply.clicked.connect(self._run_apply)
        self._btn_apply.setEnabled(False)
        actions_layout.addWidget(self._btn_apply)

        sidebar_layout.addWidget(actions_frame)

        # Progress
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(8, 4, 8, 8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("subtitleLabel")
        progress_layout.addWidget(self._progress_label)

        sidebar_layout.addWidget(progress_frame)

        splitter.addWidget(sidebar)

        # ---- Right Content (Tabs) ----
        self._tabs = QTabWidget()

        self._overview_panel = OverviewPanel()
        self._tabs.addTab(self._overview_panel, "개요")

        self._validation_panel = ValidationPanel()
        self._tabs.addTab(self._validation_panel, "검증")

        self._ebcdic_panel = EbcdicPanel()
        self._tabs.addTab(self._ebcdic_panel, "EBCDIC")

        self._binary_panel = BinaryPanel()
        self._tabs.addTab(self._binary_panel, "Binary Header")

        self._trace_panel = TracePanel()
        self._tabs.addTab(self._trace_panel, "Trace Header")

        self._batch_panel = BatchPanel()
        self._tabs.addTab(self._batch_panel, "배치 처리")

        self._log_panel = LogPanel()
        self._tabs.addTab(self._log_panel, "변경 로그")

        # Disable edit tabs initially
        for i in [2, 3, 4]:  # EBCDIC, Binary, Trace
            self._tabs.setTabEnabled(i, False)

        splitter.addWidget(self._tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = QLabel("준비 완료")
        status.addWidget(self._status_label, stretch=1)
        self._version_label = QLabel(f"v{__version__}")
        status.addPermanentWidget(self._version_label)

    def _apply_theme(self) -> None:
        qss_path = Path(__file__).parent / "theme.qss"
        if qss_path.exists():
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    # ==================================================================
    # File Selection
    # ==================================================================

    def _file_panel_open_file(self) -> None:
        self._file_panel._open_file()

    def _file_panel_open_folder(self) -> None:
        self._file_panel._open_folder()

    def _on_file_selected(self, path: str) -> None:
        """Load selected file metadata in a background thread."""
        self._status_label.setText(f"로딩: {Path(path).name}...")
        self._progress_label.setText("파일 읽는 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate

        self._engine = SegyEngine()
        self._start_worker(
            LoadWorker(self._engine, path),
            on_finished=self._on_file_loaded,
            on_error=self._on_error,
        )

    def _on_file_loaded(self, info: SegyFileInfo) -> None:
        self._current_info = info
        self._current_validation = None
        self._dry_run_executed = False
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")

        # Update panels
        self._overview_panel.update_info(info)
        self._ebcdic_panel.load_from_info(info)
        self._binary_panel.load_from_info(info)
        self._trace_panel.load_from_info(info)
        self._validation_panel.clear()

        # Enable buttons
        self._btn_validate.setEnabled(True)
        self._tabs.setCurrentIndex(0)

        self._status_label.setText(
            f"로드 완료: {info.filename} | "
            f"{info.trace_count:,} traces | "
            f"{info.samples_per_trace:,} samples"
        )
        self._log_panel.append_log(
            f"파일 로드: {info.filename} ({info.file_size_bytes:,} bytes)"
        )

    # ==================================================================
    # Validation
    # ==================================================================

    def _run_validate(self) -> None:
        if not self._current_info:
            return

        self._status_label.setText("검증 중...")
        self._progress_label.setText("검증 실행 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)

        self._start_worker(
            ValidateWorker(self._engine, self._current_info),
            on_finished=self._on_validated,
            on_error=self._on_error,
        )

    def _on_validated(self, result: ValidationResult) -> None:
        self._current_validation = result
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")

        self._validation_panel.update_result(result)
        self._tabs.setCurrentIndex(1)

        # Enable/disable edit tabs based on validation
        can_edit = result.overall_status != "FAIL"
        for i in [2, 3, 4]:
            self._tabs.setTabEnabled(i, can_edit)

        self._btn_dry_run.setEnabled(can_edit)
        self._btn_apply.setEnabled(can_edit)

        self._status_label.setText(f"검증 완료: {result.overall_status}")
        self._log_panel.append_log(
            f"검증 결과: {result.overall_status} "
            f"({len(result.checks)} checks)"
        )

        if result.overall_status == "FAIL":
            QMessageBox.warning(
                self,
                "검증 실패",
                "파일 무결성 검증에 실패했습니다.\n"
                "수정 기능이 비활성화됩니다.\n\n"
                "검증 탭에서 상세 내용을 확인하세요.",
            )

    # ==================================================================
    # Dry Run
    # ==================================================================

    def _run_dry_run(self) -> None:
        if not self._current_info:
            return

        job = self._collect_edits()
        if not job.ebcdic_edits and not job.binary_edits and not job.trace_edits:
            QMessageBox.information(self, "Dry Run", "수정할 내용이 없습니다.")
            return

        self._status_label.setText("Dry Run 미리보기 생성 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)

        self._start_worker(
            DryRunWorker(self._engine, self._current_info.path, job),
            on_finished=self._on_dry_run_done,
            on_error=self._on_error,
        )

    def _on_dry_run_done(self, preview: dict) -> None:
        self._progress_bar.setVisible(False)
        self._status_label.setText("Dry Run 완료")
        self._dry_run_executed = True

        # Show preview in log
        self._log_panel.append_log("=== Dry Run Preview ===")

        if preview.get("ebcdic_preview"):
            for p in preview["ebcdic_preview"]:
                for idx in p.get("changed_lines", []):
                    self._log_panel.append_log(
                        f"  EBCDIC line {idx+1}: changed"
                    )

        if preview.get("binary_preview"):
            for p in preview["binary_preview"]:
                self._log_panel.append_log(
                    f"  Binary {p['field']}: {p['before']} -> {p['after']}"
                )

        if preview.get("trace_preview"):
            for df in preview["trace_preview"]:
                changed = df[df["changed"] == True]
                if not changed.empty:
                    self._log_panel.append_log(
                        f"  Trace Header: {len(changed)} traces would be modified"
                    )
                    for _, row in changed.head(5).iterrows():
                        self._log_panel.append_log(
                            f"    trace {row['trace']}: "
                            f"{row['field']} {row['current']} -> {row['new']}"
                        )

        self._log_panel.append_log("=== End Preview ===")
        self._tabs.setCurrentIndex(6)  # Switch to log tab

    # ==================================================================
    # Apply Edits
    # ==================================================================

    def _run_apply(self) -> None:
        if not self._current_info:
            return

        files = self._file_panel.get_files()
        job = self._collect_edits()
        n_edits = len(job.ebcdic_edits) + len(job.binary_edits) + len(job.trace_edits)

        if n_edits == 0:
            QMessageBox.information(self, "\uc218\uc815 \uc801\uc6a9", "\uc218\uc815\ud560 \ub0b4\uc6a9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
            return

        # Step 1: Recommend Dry Run if not yet executed
        if not self._dry_run_executed:
            msg = QMessageBox(self)
            msg.setWindowTitle("\uc218\uc815 \uc801\uc6a9")
            msg.setIcon(QMessageBox.Question)
            msg.setText(
                "Dry Run(\ubbf8\ub9ac\ubcf4\uae30)\uc744 \uc544\uc9c1 \uc2e4\ud589\ud558\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.\n\n"
                "\uc218\uc815 \uc0ac\ud56d\uc744 \ubbf8\ub9ac \ud655\uc778\ud55c \ud6c4 \uc801\uc6a9\ud558\ub294 \uac83\uc744 \uad8c\uc7a5\ud569\ub2c8\ub2e4."
            )
            btn_dry = msg.addButton("Dry Run \uba3c\uc800 \uc2e4\ud589", QMessageBox.AcceptRole)
            btn_apply = msg.addButton("\ubc14\ub85c \uc801\uc6a9", QMessageBox.DestructiveRole)
            btn_cancel = msg.addButton("\ucde8\uc18c", QMessageBox.RejectRole)
            msg.setDefaultButton(btn_dry)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_dry:
                self._run_dry_run()
                return
            elif clicked == btn_cancel:
                return
            # btn_apply: continue to next steps

        output_mode = self._batch_panel.get_output_mode()
        output_dir = self._batch_panel.get_output_dir()

        # Step 2: Check for output file conflicts
        from segy_toolbox.io.writer import SegyFileWriter
        conflicts = SegyFileWriter.check_output_conflicts(
            files, output_mode, output_dir
        )
        if conflicts:
            conflict_names = "\n".join(f"  - {Path(c).name}" for c in conflicts[:10])
            extra = ""
            if len(conflicts) > 10:
                extra = f"\n  ... \uc678 {len(conflicts) - 10}\uac1c"
            reply = QMessageBox.warning(
                self,
                "\ud30c\uc77c \ub36e\uc5b4\uc4f0\uae30 \uacbd\uace0",
                f"\ub2e4\uc74c \ud30c\uc77c\uc774 \ub36e\uc5b4\uc4f0\uc5ec\uc9d1\ub2c8\ub2e4:\n\n"
                f"{conflict_names}{extra}\n\n"
                f"\uacc4\uc18d\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Step 3: Final confirmation (differentiated by output mode)
        if output_mode == "in_place_backup":
            reply = QMessageBox.warning(
                self,
                "\u26a0 \uc6d0\ubcf8 \ud30c\uc77c \uc9c1\uc811 \uc218\uc815",
                f"\u26a0 \uc6d0\ubcf8 \ud30c\uc77c \uc9c1\uc811 \uc218\uc815 \ubaa8\ub4dc\n\n"
                f"{len(files)}\uac1c \uc6d0\ubcf8 \ud30c\uc77c\uc774 \uc9c1\uc811 \uc218\uc815\ub429\ub2c8\ub2e4.\n"
                f"\uac01 \ud30c\uc77c\uc758 \ubc31\uc5c5(.bak)\uc774 \uac19\uc740 \ud3f4\ub354\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4.\n\n"
                f"\uc218\uc815\ud560 \ud56d\ubaa9: {n_edits}\uac1c\n\n"
                f"\uacc4\uc18d\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        else:
            reply = QMessageBox.question(
                self,
                "\uc218\uc815 \uc801\uc6a9 \ud655\uc778",
                f"{len(files)}\uac1c \ud30c\uc77c\uc5d0 {n_edits}\uac1c \uc218\uc815\uc744 \uc801\uc6a9\ud569\ub2c8\ub2e4.\n\n"
                f"\uc6d0\ubcf8 \ud30c\uc77c\uc740 \ubcc0\uacbd\ub418\uc9c0 \uc54a\uc73c\uba70,\n"
                f"\ubcf5\uc0ac\ubcf8\uc774 \ucd9c\ub825 \ud3f4\ub354\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4.\n\n"
                f"\ucd9c\ub825 \ud3f4\ub354: {output_dir}\n\n"
                f"\uacc4\uc18d\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?",
                QMessageBox.Yes | QMessageBox.No,
            )
        if reply != QMessageBox.Yes:
            return

        # Update engine config and execute
        self._engine.config.output_mode = output_mode
        self._engine.config.output_dir = output_dir

        if len(files) == 1:
            self._apply_single(files[0], job)
        else:
            self._apply_batch(files, job)

    def _apply_single(self, path: str, job: EditJob) -> None:
        self._status_label.setText("수정 적용 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)

        worker = ApplyWorker(self._engine, path, job)
        worker.log.connect(lambda msg: self._log_panel.append_log(msg))
        worker.progress.connect(self._on_progress)

        self._start_worker(
            worker,
            on_finished=self._on_apply_done,
            on_error=self._on_error,
        )

    def _on_apply_done(self, output_path: str, changes: list, post_val) -> None:
        self._progress_bar.setVisible(False)
        self._log_panel.append_changes(changes)

        if post_val:
            self._validation_panel.update_result(post_val)

        self._status_label.setText(
            f"수정 완료: {len(changes)} changes -> {output_path}"
        )
        self._tabs.setCurrentIndex(6)

    def _apply_batch(self, paths: list[str], job: EditJob) -> None:
        self._status_label.setText("배치 처리 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(paths))
        self._tabs.setCurrentIndex(5)

        worker = BatchWorker(self._engine, paths, job)
        worker.log.connect(lambda msg: self._log_panel.append_log(msg))
        worker.progress.connect(self._on_batch_progress)

        self._start_worker(
            worker,
            on_finished=self._on_batch_done,
            on_error=self._on_error,
        )

    def _on_batch_progress(self, current: int, total: int) -> None:
        self._progress_bar.setValue(current)
        self._batch_panel.show_progress(current, total)
        self._progress_label.setText(f"파일 {current}/{total}")

    def _on_batch_done(self, results: list) -> None:
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")
        self._batch_panel.display_results(results)

        total_changes = sum(len(r.changes) for r in results)
        self._status_label.setText(
            f"배치 완료: {len(results)} files, {total_changes} changes"
        )

        for r in results:
            if r.changes:
                self._log_panel.append_changes(r.changes)

    # ==================================================================
    # Helpers
    # ==================================================================

    def _collect_edits(self) -> EditJob:
        """Collect all pending edits from the GUI panels."""
        job = EditJob()

        # EBCDIC
        ebcdic_edit = self._ebcdic_panel.get_edit()
        if ebcdic_edit:
            job.ebcdic_edits.append(ebcdic_edit)

        # Binary header
        job.binary_edits = self._binary_panel.get_edits()

        # Trace headers
        job.trace_edits = self._trace_panel.get_edits()

        return job

    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)

    def _on_error(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")
        self._status_label.setText(f"오류 발생")
        self._log_panel.append_log(f"ERROR: {message}")
        QMessageBox.critical(self, "오류", message)

    def _start_worker(self, worker, on_finished, on_error) -> None:
        """Start a worker in a background thread."""
        # Clean up previous thread
        self._safe_stop_previous_thread()

        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        # thread.quit must use QueuedConnection because the signal is
        # emitted from the worker living inside the thread.  A direct
        # call would trigger "QThread::wait: Thread tried to wait on itself".
        worker.finished.connect(thread.quit, Qt.QueuedConnection)
        worker.error.connect(thread.quit, Qt.QueuedConnection)

        # prevent GC
        self._worker_thread = thread
        self._current_worker = worker

        thread.start()

    def _safe_stop_previous_thread(self) -> None:
        """Safely stop and clean up the previous worker thread."""
        thread = self._worker_thread
        if thread is None:
            return
        try:
            if thread.isRunning():
                thread.quit()
                if not thread.wait(5000):
                    thread.terminate()
                    thread.wait(2000)
        except RuntimeError:
            # C++ object already deleted — just clear the reference
            pass
        self._worker_thread = None
        self._current_worker = None


def main():
    """Launch the GUI application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("SEG-Y Batch Inspector & Fixer")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
