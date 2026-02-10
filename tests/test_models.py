"""Tests for data models."""

from __future__ import annotations

from segy_toolbox.models import (
    FORMAT_BPS,
    FORMAT_NAMES,
    BatchResult,
    BinaryHeaderEdit,
    ChangeRecord,
    EbcdicEdit,
    EditJob,
    PipelineState,
    SegyFileInfo,
    TraceHeaderEdit,
    ValidationCheck,
    ValidationResult,
)


class TestFormatMaps:
    def test_format_bps_has_all_standard_codes(self):
        assert 1 in FORMAT_BPS  # IBM Float
        assert 2 in FORMAT_BPS  # 4-byte Integer
        assert 3 in FORMAT_BPS  # 2-byte Integer
        assert 5 in FORMAT_BPS  # IEEE Float

    def test_format_names_matches_bps(self):
        assert set(FORMAT_NAMES.keys()) == set(FORMAT_BPS.keys())


class TestPipelineState:
    def test_enum_values(self):
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.FILES_LOADED.value == "files_loaded"
        assert PipelineState.VALIDATED.value == "validated"
        assert PipelineState.APPLIED.value == "applied"


class TestSegyFileInfo:
    def test_default_values(self):
        info = SegyFileInfo()
        assert info.path == ""
        assert info.trace_count == 0
        assert info.ebcdic_lines == []
        assert info.binary_header == {}
        assert info.trace_header_summary == {}

    def test_custom_values(self):
        info = SegyFileInfo(
            path="/test.segy",
            filename="test.segy",
            trace_count=100,
            samples_per_trace=500,
            sample_interval=2000,
            format_code=1,
        )
        assert info.filename == "test.segy"
        assert info.trace_count == 100
        assert info.format_code == 1


class TestValidationCheck:
    def test_default_status(self):
        check = ValidationCheck(name="Test")
        assert check.status == "PASS"

    def test_fail_check(self):
        check = ValidationCheck(
            name="Size Check",
            category="structure",
            status="FAIL",
            message="File too small",
        )
        assert check.status == "FAIL"
        assert check.category == "structure"


class TestValidationResult:
    def test_auto_timestamp(self):
        result = ValidationResult(filename="test.segy")
        assert result.timestamp != ""

    def test_overall_status_default(self):
        result = ValidationResult()
        assert result.overall_status == "PASS"


class TestEditModels:
    def test_ebcdic_edit_defaults(self):
        edit = EbcdicEdit()
        assert edit.mode == "lines"
        assert edit.lines == {}

    def test_binary_header_edit(self):
        edit = BinaryHeaderEdit(
            field_name="sample_interval",
            value=4000,
            dtype="int16",
        )
        assert edit.field_name == "sample_interval"
        assert edit.value == 4000

    def test_trace_header_edit_expression_mode(self):
        edit = TraceHeaderEdit(
            field_name="source_x",
            mode="expression",
            expression="source_x * 100",
        )
        assert edit.mode == "expression"
        assert edit.expression == "source_x * 100"

    def test_edit_job_empty(self):
        job = EditJob()
        assert job.ebcdic_edits == []
        assert job.binary_edits == []
        assert job.trace_edits == []


class TestChangeRecord:
    def test_auto_timestamp(self):
        record = ChangeRecord(filename="test.segy", field_name="source_x")
        assert record.timestamp != ""

    def test_trace_index_optional(self):
        record = ChangeRecord()
        assert record.trace_index is None


class TestBatchResult:
    def test_default_status(self):
        result = BatchResult()
        assert result.status == "SUCCESS"
        assert result.changes == []
        assert result.duration_seconds == 0.0
