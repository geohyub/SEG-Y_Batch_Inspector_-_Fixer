"""Tests for EBCDIC and binary header editors."""

from __future__ import annotations

import pytest

from segy_toolbox.core.ebcdic_editor import EbcdicEditor
from segy_toolbox.core.binary_editor import BinaryHeaderEditor
from segy_toolbox.core.trace_editor import TraceHeaderEditor
from segy_toolbox.io.ebcdic import COLS, LINES
from segy_toolbox.models import (
    BinaryHeaderEdit,
    EbcdicEdit,
    TraceHeaderEdit,
)


class TestEbcdicEditor:
    def setup_method(self):
        self.editor = EbcdicEditor()
        self.original_lines = [f"C{i+1:02d} ORIGINAL LINE {i+1}".ljust(COLS) for i in range(LINES)]

    def test_apply_line_edit(self):
        edit = EbcdicEdit(mode="lines", lines={0: "C01 MODIFIED LINE"})
        new_lines = self.editor.apply_edit(self.original_lines, edit)
        assert new_lines[0].startswith("C01 MODIFIED LINE")
        assert new_lines[1] == self.original_lines[1]

    def test_apply_multiple_lines(self):
        edit = EbcdicEdit(mode="lines", lines={0: "NEW 1", 5: "NEW 6", 39: "NEW 40"})
        new_lines = self.editor.apply_edit(self.original_lines, edit)
        assert new_lines[0].startswith("NEW 1")
        assert new_lines[5].startswith("NEW 6")
        assert new_lines[39].startswith("NEW 40")

    def test_line_padded_to_80(self):
        edit = EbcdicEdit(mode="lines", lines={0: "SHORT"})
        new_lines = self.editor.apply_edit(self.original_lines, edit)
        assert len(new_lines[0]) == COLS

    def test_line_truncated_to_80(self):
        edit = EbcdicEdit(mode="lines", lines={0: "X" * 200})
        new_lines = self.editor.apply_edit(self.original_lines, edit)
        assert len(new_lines[0]) == COLS

    def test_invalid_line_index_ignored(self):
        edit = EbcdicEdit(mode="lines", lines={-1: "BAD", 50: "ALSO BAD"})
        new_lines = self.editor.apply_edit(self.original_lines, edit)
        assert new_lines == self.original_lines

    def test_preview_returns_changed_indices(self):
        edit = EbcdicEdit(mode="lines", lines={0: "CHANGED", 3: "ALSO CHANGED"})
        new_lines, changed = self.editor.preview(self.original_lines, edit)
        assert 0 in changed
        assert 3 in changed
        assert 1 not in changed

    def test_preview_no_change(self):
        edit = EbcdicEdit(mode="lines", lines={})
        new_lines, changed = self.editor.preview(self.original_lines, edit)
        assert changed == []

    def test_encode_decode_roundtrip(self):
        encoded = self.editor.encode(self.original_lines, "EBCDIC")
        decoded = self.editor.get_lines(encoded)
        assert decoded == self.original_lines

    def test_short_input_padded(self):
        short_lines = ["C01 ONLY".ljust(COLS)]
        edit = EbcdicEdit(mode="lines", lines={})
        new_lines = self.editor.apply_edit(short_lines, edit)
        assert len(new_lines) == LINES


class TestBinaryHeaderEditor:
    def setup_method(self):
        self.editor = BinaryHeaderEditor()

    def test_resolve_field_by_name(self):
        edit = BinaryHeaderEdit(field_name="sample_interval")
        field = self.editor.resolve_field(edit)
        assert isinstance(field, int)

    def test_resolve_field_by_offset(self):
        edit = BinaryHeaderEdit(byte_offset=17)
        field = self.editor.resolve_field(edit)
        assert isinstance(field, int)

    def test_resolve_unknown_raises(self):
        edit = BinaryHeaderEdit(field_name="nonexistent_field")
        with pytest.raises(ValueError, match="Cannot resolve"):
            self.editor.resolve_field(edit)

    def test_get_display_name(self):
        edit = BinaryHeaderEdit(field_name="sample_interval")
        name = self.editor.get_display_name(edit)
        assert name == "sample_interval"

    def test_get_display_name_by_offset(self):
        edit = BinaryHeaderEdit(byte_offset=17)
        name = self.editor.get_display_name(edit)
        assert "sample_interval" in name

    def test_preview_edit(self):
        current_values = {"sample_interval": 2000}
        edit = BinaryHeaderEdit(field_name="sample_interval", value=4000)
        name, before, after = self.editor.preview_edit(current_values, edit)
        assert name == "sample_interval"
        assert before == 2000
        assert after == 4000

    def test_get_all_fields(self):
        fields = BinaryHeaderEditor.get_all_fields()
        assert len(fields) > 0
        assert all("name" in f for f in fields)
        assert all("dtype" in f for f in fields)


class TestTraceHeaderEditor:
    def setup_method(self):
        self.editor = TraceHeaderEditor()

    def test_resolve_field_by_name(self):
        edit = TraceHeaderEdit(field_name="source_x")
        field = self.editor.resolve_field(edit)
        assert isinstance(field, int)

    def test_resolve_unknown_raises(self):
        edit = TraceHeaderEdit(field_name="nonexistent")
        with pytest.raises(ValueError, match="Cannot resolve"):
            self.editor.resolve_field(edit)

    def test_validate_valid_expression(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="expression",
            expression="source_x * 100",
        )
        err = self.editor.validate_edit(edit)
        assert err is None

    def test_validate_invalid_expression(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="expression",
            expression="unknown_var * 100",
        )
        err = self.editor.validate_edit(edit)
        assert err is not None
        assert "Expression error" in err

    def test_validate_invalid_condition(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="set",
            value=0,
            condition="bad_var > 0",
        )
        err = self.editor.validate_edit(edit)
        assert err is not None
        assert "Condition error" in err

    def test_validate_unknown_field_without_offset(self):
        edit = TraceHeaderEdit(field_name="totally_unknown", mode="set", value=0)
        err = self.editor.validate_edit(edit)
        assert err is not None
        assert "Unknown field" in err

    def test_validate_copy_unknown_source(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="copy",
            source_field="nonexistent",
        )
        err = self.editor.validate_edit(edit)
        assert err is not None
        assert "Unknown source field" in err

    def test_validate_csv_missing_file(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="csv_import",
            csv_path="/nonexistent/file.csv",
        )
        err = self.editor.validate_edit(edit)
        assert err is not None
        assert "CSV file not found" in err

    def test_get_all_fields(self):
        fields = TraceHeaderEditor.get_all_fields()
        assert len(fields) > 0
        assert any(f["name"] == "source_x" for f in fields)
