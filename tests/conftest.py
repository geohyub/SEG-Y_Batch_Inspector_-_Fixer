"""Shared test fixtures for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest


def _make_segy_bytes(
    *,
    n_traces: int = 10,
    samples_per_trace: int = 100,
    sample_interval: int = 2000,
    format_code: int = 1,
    ebcdic_text: str | None = None,
) -> bytes:
    """Create a minimal valid SEG-Y byte stream in memory.

    Structure: 3200-byte textual header + 400-byte binary header + traces.
    Each trace = 240-byte trace header + samples * 4 bytes (IBM float / IEEE).
    """
    bps = {1: 4, 2: 4, 3: 2, 5: 4, 6: 8, 8: 1}.get(format_code, 4)

    # --- EBCDIC textual header (3200 bytes) ---
    if ebcdic_text is None:
        ebcdic_text = "C01 TEST SEGY FILE".ljust(80)
        ebcdic_text += "".join(f"C{i+2:02d}".ljust(80) for i in range(39))
    else:
        ebcdic_text = ebcdic_text[:3200].ljust(3200)
    textual_header = ebcdic_text.encode("cp500")[:3200].ljust(3200, b"\x40")

    # --- Binary file header (400 bytes) ---
    binary_header = bytearray(400)
    # Bytes 17-18: sample interval (int16 big-endian)
    struct.pack_into(">h", binary_header, 16, sample_interval)
    # Bytes 21-22: samples per trace (int16 big-endian)
    struct.pack_into(">h", binary_header, 20, samples_per_trace)
    # Bytes 25-26: data format code (int16 big-endian)
    struct.pack_into(">h", binary_header, 24, format_code)

    # --- Traces ---
    trace_data = bytearray()
    for i in range(n_traces):
        # Trace header (240 bytes)
        th = bytearray(240)
        # Bytes 1-4: trace sequence number within line (int32 big-endian)
        struct.pack_into(">i", th, 0, i + 1)
        # Bytes 5-8: trace sequence number within file
        struct.pack_into(">i", th, 4, i + 1)
        # Bytes 73-76: source X (int32 big-endian)
        struct.pack_into(">i", th, 72, 500000 + i * 100)
        # Bytes 77-80: source Y (int32 big-endian)
        struct.pack_into(">i", th, 76, 6000000 + i * 50)
        # Bytes 115-116: samples per trace in this trace (int16)
        struct.pack_into(">h", th, 114, samples_per_trace)
        # Bytes 117-118: sample interval for this trace (int16)
        struct.pack_into(">h", th, 116, sample_interval)
        trace_data.extend(th)
        # Sample data (zeros)
        trace_data.extend(b"\x00" * (samples_per_trace * bps))

    return bytes(textual_header + binary_header + trace_data)


@pytest.fixture
def tmp_segy(tmp_path: Path) -> Path:
    """Create a temporary valid SEG-Y file and return its path."""
    segy_path = tmp_path / "test.segy"
    segy_path.write_bytes(_make_segy_bytes())
    return segy_path


@pytest.fixture
def tmp_segy_small(tmp_path: Path) -> Path:
    """Create a small SEG-Y file (3 traces, 50 samples)."""
    segy_path = tmp_path / "small.segy"
    segy_path.write_bytes(
        _make_segy_bytes(n_traces=3, samples_per_trace=50)
    )
    return segy_path
