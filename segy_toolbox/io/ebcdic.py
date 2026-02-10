"""EBCDIC <-> ASCII codec utilities for SEG-Y textual headers."""

from __future__ import annotations

EBCDIC_CODEC = "cp500"  # IBM EBCDIC International
LINES = 40
COLS = 80
HEADER_SIZE = LINES * COLS  # 3200 bytes


def decode_textual_header(raw: bytes) -> list[str]:
    """Decode 3200 bytes into 40 lines of 80 characters.

    Automatically detects EBCDIC vs ASCII encoding.
    """
    encoding = detect_encoding(raw)
    codec = EBCDIC_CODEC if encoding == "EBCDIC" else "ascii"
    text = raw[:HEADER_SIZE].decode(codec, errors="replace")
    return [text[i * COLS : (i + 1) * COLS] for i in range(LINES)]


def encode_textual_header(lines: list[str], encoding: str = "EBCDIC") -> bytes:
    """Encode 40 lines of text into 3200 bytes.

    Each line is padded/truncated to exactly 80 characters.
    """
    codec = EBCDIC_CODEC if encoding == "EBCDIC" else "ascii"
    padded: list[str] = []
    for line in lines[:LINES]:
        padded.append(line[:COLS].ljust(COLS))
    while len(padded) < LINES:
        padded.append(" " * COLS)
    return "".join(padded).encode(codec, errors="replace")


def detect_encoding(raw: bytes) -> str:
    """Detect whether 3200-byte textual header is EBCDIC or ASCII.

    Heuristic: count printable characters under each assumption.
    EBCDIC printable range: 0x40-0xFE
    ASCII printable range: 0x20-0x7E
    """
    if len(raw) < HEADER_SIZE:
        return "ASCII"
    sample = raw[:HEADER_SIZE]
    ebcdic_printable = sum(1 for b in sample if 0x40 <= b <= 0xFE)
    ascii_printable = sum(1 for b in sample if 0x20 <= b <= 0x7E)
    return "EBCDIC" if ebcdic_printable > ascii_printable else "ASCII"


def apply_template(template_text: str, replacements: dict[str, str]) -> list[str]:
    """Apply placeholder replacements to template text.

    Template uses {{placeholder_name}} syntax.
    Returns 40 lines of 80 characters.
    """
    for key, value in replacements.items():
        template_text = template_text.replace(f"{{{{{key}}}}}", value)

    raw_lines = template_text.splitlines()
    result: list[str] = []
    for line in raw_lines[:LINES]:
        result.append(line[:COLS].ljust(COLS))
    while len(result) < LINES:
        result.append(" " * COLS)
    return result


def load_template_file(path: str) -> str:
    """Load an EBCDIC template text file."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def format_lines_display(lines: list[str]) -> str:
    """Format 40 lines for display with line numbers (C01-C40)."""
    parts: list[str] = []
    for i, line in enumerate(lines):
        parts.append(f"C{i + 1:02d} {line}")
    return "\n".join(parts)
