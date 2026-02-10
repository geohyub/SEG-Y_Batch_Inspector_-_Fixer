"""Tests for EBCDIC codec utilities."""

from __future__ import annotations

from segy_toolbox.io.ebcdic import (
    COLS,
    HEADER_SIZE,
    LINES,
    apply_template,
    decode_textual_header,
    detect_encoding,
    encode_textual_header,
    format_lines_display,
    load_template_file,
)


class TestConstants:
    def test_lines(self):
        assert LINES == 40

    def test_cols(self):
        assert COLS == 80

    def test_header_size(self):
        assert HEADER_SIZE == 3200


class TestDetectEncoding:
    def test_ebcdic_detection(self):
        text = "C01 TEST HEADER".ljust(80) * 40
        raw = text.encode("cp500")
        assert detect_encoding(raw) == "EBCDIC"

    def test_ascii_detection(self):
        text = "C01 TEST HEADER".ljust(80) * 40
        raw = text.encode("ascii")
        assert detect_encoding(raw) == "ASCII"

    def test_short_input(self):
        assert detect_encoding(b"short") == "ASCII"


class TestDecodeTextualHeader:
    def test_decode_ebcdic(self):
        text = "".join(f"C{i+1:02d} LINE {i+1}".ljust(80) for i in range(40))
        raw = text.encode("cp500")
        lines = decode_textual_header(raw)
        assert len(lines) == 40
        assert lines[0].startswith("C01 LINE 1")

    def test_decode_ascii(self):
        text = "".join(f"C{i+1:02d} LINE {i+1}".ljust(80) for i in range(40))
        raw = text.encode("ascii")
        lines = decode_textual_header(raw)
        assert len(lines) == 40
        assert lines[0].startswith("C01 LINE 1")

    def test_output_line_count(self):
        raw = b"\x40" * 3200  # EBCDIC spaces
        lines = decode_textual_header(raw)
        assert len(lines) == 40

    def test_line_length(self):
        raw = b"\x40" * 3200
        lines = decode_textual_header(raw)
        assert all(len(line) == 80 for line in lines)


class TestEncodeTextualHeader:
    def test_encode_ebcdic(self):
        lines = ["C01 TEST".ljust(80)] + [" " * 80] * 39
        result = encode_textual_header(lines, "EBCDIC")
        assert len(result) == 3200

    def test_encode_ascii(self):
        lines = ["C01 TEST".ljust(80)] + [" " * 80] * 39
        result = encode_textual_header(lines, "ASCII")
        assert len(result) == 3200

    def test_roundtrip_ebcdic(self):
        lines = [f"C{i+1:02d} LINE {i+1}".ljust(80) for i in range(40)]
        encoded = encode_textual_header(lines, "EBCDIC")
        decoded = decode_textual_header(encoded)
        assert decoded == lines

    def test_padding_short_input(self):
        lines = ["C01 ONLY ONE LINE".ljust(80)]
        result = encode_textual_header(lines, "EBCDIC")
        assert len(result) == 3200

    def test_truncation_long_line(self):
        lines = ["X" * 200] + [" " * 80] * 39
        result = encode_textual_header(lines, "EBCDIC")
        assert len(result) == 3200


class TestApplyTemplate:
    def test_basic_replacement(self):
        template = "CLIENT: {{client_name}}\nPROJECT: {{project}}"
        replacements = {
            "client_name": "ACME Corp",
            "project": "Seismic Survey 2024",
        }
        lines = apply_template(template, replacements)
        assert "ACME Corp" in lines[0]
        assert "Seismic Survey 2024" in lines[1]

    def test_output_has_40_lines(self):
        template = "LINE 1\nLINE 2"
        lines = apply_template(template, {})
        assert len(lines) == 40

    def test_each_line_is_80_chars(self):
        template = "SHORT"
        lines = apply_template(template, {})
        assert all(len(line) == 80 for line in lines)


class TestFormatLinesDisplay:
    def test_format(self):
        lines = [f"Line {i+1}".ljust(80) for i in range(40)]
        display = format_lines_display(lines)
        assert "C01 Line 1" in display
        assert "C40 Line 40" in display

    def test_line_count(self):
        lines = [" " * 80] * 40
        display = format_lines_display(lines)
        assert display.count("\n") == 39  # 40 lines, 39 newlines


class TestLoadTemplateFile:
    def test_load(self, tmp_path):
        template_file = tmp_path / "template.txt"
        template_file.write_text("C01 TEMPLATE LINE 1\nC02 LINE 2", encoding="utf-8")
        text = load_template_file(str(template_file))
        assert "TEMPLATE LINE 1" in text
