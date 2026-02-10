"""EBCDIC textual header viewer and editor panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.core.ebcdic_editor import EbcdicEditor
from segy_toolbox.io.ebcdic import COLS, LINES, format_lines_display
from segy_toolbox.models import EbcdicEdit, SegyFileInfo


class EbcdicPanel(QWidget):
    """40-line x 80-column EBCDIC header editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = EbcdicEditor()
        self._original_lines: list[str] = []
        self._current_lines: list[str] = []
        self._encoding: str = "EBCDIC"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        enc_label = QLabel("Encoding:")
        toolbar.addWidget(enc_label)
        self._enc_display = QLabel("EBCDIC")
        self._enc_display.setStyleSheet("color: #89b4fa; font-weight: 600;")
        toolbar.addWidget(self._enc_display)

        toolbar.addStretch()

        self._btn_template = QPushButton("템플릿 로드")
        self._btn_template.clicked.connect(self._load_template)
        toolbar.addWidget(self._btn_template)

        self._btn_reset = QPushButton("원본 복원")
        self._btn_reset.clicked.connect(self._reset_to_original)
        toolbar.addWidget(self._btn_reset)

        layout.addLayout(toolbar)

        # Text editor (monospace, 80 columns)
        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._text_edit.setTabStopDistance(32)
        self._text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._text_edit, stretch=1)

        # Status bar
        status_row = QHBoxLayout()
        self._char_count = QLabel("0 / 3200 chars")
        self._char_count.setObjectName("subtitleLabel")
        status_row.addWidget(self._char_count)

        status_row.addStretch()

        self._change_count = QLabel("")
        self._change_count.setStyleSheet("color: #f9e2af;")
        status_row.addWidget(self._change_count)

        layout.addLayout(status_row)

    def load_from_info(self, info: SegyFileInfo) -> None:
        """Load EBCDIC content from file info."""
        self._original_lines = list(info.ebcdic_lines)
        self._current_lines = list(info.ebcdic_lines)
        self._encoding = info.ebcdic_encoding
        self._enc_display.setText(info.ebcdic_encoding)
        self._display_lines(self._current_lines)

    def get_edit(self) -> EbcdicEdit | None:
        """Build an EbcdicEdit from current editor state.

        Returns None if no changes were made.
        """
        current = self._parse_editor_text()
        changes: dict[int, str] = {}
        for i in range(LINES):
            orig = self._original_lines[i] if i < len(self._original_lines) else " " * COLS
            curr = current[i] if i < len(current) else " " * COLS
            if orig != curr:
                changes[i] = curr

        if not changes:
            return None

        return EbcdicEdit(mode="lines", lines=changes)

    def clear(self) -> None:
        self._original_lines = []
        self._current_lines = []
        self._text_edit.clear()
        self._char_count.setText("0 / 3200 chars")
        self._change_count.setText("")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _load_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "EBCDIC 템플릿 파일 선택", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            from segy_toolbox.io.ebcdic import load_template_file, apply_template
            template_text = load_template_file(path)
            lines = apply_template(template_text, {})
            self._current_lines = lines
            self._display_lines(lines)

    def _reset_to_original(self) -> None:
        if self._original_lines:
            self._current_lines = list(self._original_lines)
            self._display_lines(self._current_lines)

    def _on_text_changed(self) -> None:
        text = self._text_edit.toPlainText()
        total_chars = len(text.replace("\n", ""))
        self._char_count.setText(f"{total_chars} / 3200 chars")

        # Count changed lines
        current = self._parse_editor_text()
        n_changed = 0
        for i in range(LINES):
            orig = self._original_lines[i] if i < len(self._original_lines) else " " * COLS
            curr = current[i] if i < len(current) else " " * COLS
            if orig.rstrip() != curr.rstrip():
                n_changed += 1

        if n_changed > 0:
            self._change_count.setText(f"{n_changed} line(s) changed")
        else:
            self._change_count.setText("")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _display_lines(self, lines: list[str]) -> None:
        """Display lines in the text editor with C01-C40 prefixes."""
        self._text_edit.blockSignals(True)
        self._text_edit.setPlainText(format_lines_display(lines))
        self._text_edit.blockSignals(False)
        self._on_text_changed()

    def _parse_editor_text(self) -> list[str]:
        """Parse editor text back into 40 lines of 80 chars."""
        text = self._text_edit.toPlainText()
        raw_lines = text.split("\n")
        result: list[str] = []

        for raw_line in raw_lines:
            # Strip C01-C40 prefix if present
            if len(raw_line) >= 4 and raw_line[0] == "C" and raw_line[1:3].isdigit():
                content = raw_line[4:]  # Skip "CXX "
            else:
                content = raw_line
            result.append(content[:COLS].ljust(COLS))

        # Pad to 40 lines
        while len(result) < LINES:
            result.append(" " * COLS)

        return result[:LINES]
