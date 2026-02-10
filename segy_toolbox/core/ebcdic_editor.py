"""EBCDIC textual header editor."""

from __future__ import annotations

from pathlib import Path

from segy_toolbox.io.ebcdic import (
    COLS,
    LINES,
    apply_template,
    decode_textual_header,
    encode_textual_header,
    load_template_file,
)
from segy_toolbox.models import EbcdicEdit


class EbcdicEditor:
    """Edit the 3200-byte EBCDIC textual header of a SEG-Y file."""

    def get_lines(self, ebcdic_raw: bytes) -> list[str]:
        """Decode EBCDIC header into 40 lines of 80 chars."""
        return decode_textual_header(ebcdic_raw)

    def apply_edit(
        self, current_lines: list[str], edit: EbcdicEdit
    ) -> list[str]:
        """Apply an EbcdicEdit to current lines and return new lines."""
        if edit.mode == "template":
            return self._apply_template(edit)
        elif edit.mode == "lines":
            return self._apply_line_edits(current_lines, edit.lines)
        return list(current_lines)

    def encode(self, lines: list[str], encoding: str = "EBCDIC") -> bytes:
        """Encode 40 lines back to 3200 bytes."""
        return encode_textual_header(lines, encoding)

    def preview(
        self, current_lines: list[str], edit: EbcdicEdit
    ) -> tuple[list[str], list[int]]:
        """Preview changes: return (new_lines, list of changed line indices)."""
        new_lines = self.apply_edit(current_lines, edit)
        changed = [
            i for i in range(LINES)
            if i < len(current_lines)
            and i < len(new_lines)
            and current_lines[i] != new_lines[i]
        ]
        return new_lines, changed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_template(self, edit: EbcdicEdit) -> list[str]:
        """Load and apply an EBCDIC template file with replacements."""
        if not edit.template_path:
            raise ValueError("Template path is required for template mode")
        template_text = load_template_file(edit.template_path)
        return apply_template(template_text, edit.template_replacements)

    @staticmethod
    def _apply_line_edits(
        current_lines: list[str], line_edits: dict[int, str]
    ) -> list[str]:
        """Apply line-level edits to existing text."""
        new_lines = list(current_lines)
        while len(new_lines) < LINES:
            new_lines.append(" " * COLS)

        for line_idx, new_text in line_edits.items():
            if 0 <= line_idx < LINES:
                new_lines[line_idx] = new_text[:COLS].ljust(COLS)

        return new_lines
