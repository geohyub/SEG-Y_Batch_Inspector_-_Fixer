"""Data models for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PipelineState(Enum):
    IDLE = "idle"
    FILES_LOADED = "files_loaded"
    VALIDATED = "validated"
    EDITS_DEFINED = "edits_defined"
    APPLIED = "applied"


# ---------------------------------------------------------------------------
# SEG-Y format code -> bytes per sample
# ---------------------------------------------------------------------------

FORMAT_BPS: dict[int, int] = {
    1: 4,   # IBM Float
    2: 4,   # 4-byte Integer
    3: 2,   # 2-byte Integer
    5: 4,   # IEEE Float
    6: 8,   # IEEE Double (rare)
    8: 1,   # 1-byte Integer
}

FORMAT_NAMES: dict[int, str] = {
    1: "IBM Float (4-byte)",
    2: "4-byte Integer",
    3: "2-byte Integer",
    5: "IEEE Float (4-byte)",
    6: "IEEE Double (8-byte)",
    8: "1-byte Integer",
}


# ---------------------------------------------------------------------------
# File metadata
# ---------------------------------------------------------------------------

@dataclass
class SegyFileInfo:
    """Metadata extracted from an opened SEG-Y file."""

    path: str = ""
    filename: str = ""
    file_size_bytes: int = 0

    # EBCDIC textual header
    ebcdic_lines: list[str] = field(default_factory=list)
    ebcdic_encoding: str = "EBCDIC"  # "EBCDIC" or "ASCII"
    ebcdic_raw: bytes = b""

    # Binary file header
    format_code: int = 0
    sample_interval: int = 0       # microseconds
    samples_per_trace: int = 0
    trace_count: int = 0
    bytes_per_sample: int = 0
    expected_file_size: int = 0
    binary_header: dict[str, int] = field(default_factory=dict)

    # Trace header summary (sampled statistics)
    trace_header_summary: dict[str, dict[str, float]] = field(default_factory=dict)
    coordinate_scalar: int = 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationCheck:
    """Single validation check result."""

    name: str = ""
    category: str = ""        # "structure", "binary_header", "trace_header", "post_edit"
    status: str = "PASS"      # "PASS", "FAIL", "WARNING"
    message: str = ""
    details: str = ""


@dataclass
class ValidationResult:
    """Complete validation result for one file."""

    filename: str = ""
    overall_status: str = "PASS"
    checks: list[ValidationCheck] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Edit operations
# ---------------------------------------------------------------------------

@dataclass
class EbcdicEdit:
    """EBCDIC textual header edit operation."""

    mode: str = "lines"          # "lines" or "template"
    lines: dict[int, str] = field(default_factory=dict)  # line_index -> new text
    template_path: str = ""
    template_replacements: dict[str, str] = field(default_factory=dict)


@dataclass
class BinaryHeaderEdit:
    """Binary file header edit operation."""

    field_name: str = ""         # segyio BinField name or ""
    byte_offset: int | None = None
    value: int | float = 0
    dtype: str = "int16"         # "int16", "int32", "uint16", "uint32", "float32"


@dataclass
class TraceHeaderEdit:
    """Trace header batch edit operation."""

    field_name: str = ""         # segyio TraceField name or ""
    byte_offset: int | None = None
    mode: str = "set"            # "set", "expression", "copy", "csv_import"
    value: int | float | None = None
    expression: str = ""         # e.g., "source_x * 100"
    condition: str = ""          # e.g., "trace_sequence_number_within_line > 100"
    source_field: str = ""       # for "copy" mode
    csv_path: str = ""           # for "csv_import" mode
    csv_column: str = ""
    dtype: str = "int32"


@dataclass
class EditJob:
    """A collection of edit operations to apply to a file."""

    ebcdic_edits: list[EbcdicEdit] = field(default_factory=list)
    binary_edits: list[BinaryHeaderEdit] = field(default_factory=list)
    trace_edits: list[TraceHeaderEdit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Change log
# ---------------------------------------------------------------------------

@dataclass
class ChangeRecord:
    """One field change for the change log."""

    filename: str = ""
    timestamp: str = ""
    field_type: str = ""         # "ebcdic", "binary_header", "trace_header"
    field_name: str = ""
    trace_index: int | None = None
    before_value: str = ""
    after_value: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

@dataclass
class BatchResult:
    """Result for one file in a batch operation."""

    filename: str = ""
    status: str = "SUCCESS"      # "SUCCESS", "FAILURE", "SKIPPED"
    message: str = ""
    changes: list[ChangeRecord] = field(default_factory=list)
    validation_before: ValidationResult | None = None
    validation_after: ValidationResult | None = None
    duration_seconds: float = 0.0
