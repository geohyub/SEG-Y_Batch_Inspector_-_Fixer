"""File selection sidebar panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SEGY_FILTER = "SEG-Y Files (*.segy *.sgy *.seg *.SEGY *.SGY);;All Files (*)"
SEGY_EXTENSIONS = {".segy", ".sgy", ".seg"}


class FilePanel(QWidget):
    """Left sidebar for file selection and management."""

    file_selected = Signal(str)        # Emitted when a file is clicked
    files_changed = Signal(list)       # Emitted when file list changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("SEG-Y Files")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_file = QPushButton("파일 열기")
        btn_file.clicked.connect(self._open_file)
        btn_row.addWidget(btn_file)

        btn_folder = QPushButton("폴더 열기")
        btn_folder.clicked.connect(self._open_folder)
        btn_row.addWidget(btn_folder)

        layout.addLayout(btn_row)

        # File list
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, stretch=1)

        # Status
        self._status_label = QLabel("파일을 선택하세요")
        self._status_label.setObjectName("subtitleLabel")
        layout.addWidget(self._status_label)

        # Remove button
        btn_remove = QPushButton("선택 파일 제거")
        btn_remove.clicked.connect(self._remove_selected)
        layout.addWidget(btn_remove)

        # Clear button
        btn_clear = QPushButton("전체 초기화")
        btn_clear.setObjectName("dangerButton")
        btn_clear.clicked.connect(self._clear_all)
        layout.addWidget(btn_clear)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_files(self) -> list[str]:
        return list(self._files)

    def get_selected_file(self) -> str | None:
        row = self._list.currentRow()
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def add_files(self, paths: list[str | Path]) -> None:
        for p in paths:
            p_str = str(p)
            if p_str not in self._files:
                self._files.append(p_str)
                item = QListWidgetItem(Path(p_str).name)
                item.setToolTip(p_str)
                self._list.addItem(item)
        self._update_status()
        self.files_changed.emit(self._files)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "SEG-Y 파일 선택", "", SEGY_FILTER
        )
        if paths:
            self.add_files(paths)
            self._list.setCurrentRow(self._list.count() - 1)

    def _open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "SEG-Y 파일이 있는 폴더 선택"
        )
        if folder:
            folder_path = Path(folder)
            segy_files = sorted(
                f for f in folder_path.iterdir()
                if f.suffix.lower() in SEGY_EXTENSIONS
            )
            if segy_files:
                self.add_files(segy_files)
            else:
                self._status_label.setText("SEG-Y 파일을 찾을 수 없습니다")

    def _on_selection_changed(self, row: int) -> None:
        if 0 <= row < len(self._files):
            self.file_selected.emit(self._files[row])

    def _remove_selected(self) -> None:
        row = self._list.currentRow()
        if 0 <= row < len(self._files):
            self._files.pop(row)
            self._list.takeItem(row)
            self._update_status()
            self.files_changed.emit(self._files)

    def _clear_all(self) -> None:
        self._files.clear()
        self._list.clear()
        self._update_status()
        self.files_changed.emit(self._files)

    def _update_status(self) -> None:
        n = len(self._files)
        if n == 0:
            self._status_label.setText("파일을 선택하세요")
        else:
            self._status_label.setText(f"{n}개 파일 로드됨")

    # ------------------------------------------------------------------
    # Drag & Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in SEGY_EXTENSIONS:
                paths.append(p)
            elif p.is_dir():
                paths.extend(
                    f for f in p.iterdir()
                    if f.suffix.lower() in SEGY_EXTENSIONS
                )
        if paths:
            self.add_files(sorted(paths))
