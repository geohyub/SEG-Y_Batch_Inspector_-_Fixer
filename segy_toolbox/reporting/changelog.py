"""CSV change log writer."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from segy_toolbox.models import ChangeRecord


def write_changelog_csv(
    changes: list[ChangeRecord],
    output_path: str | Path,
) -> str:
    """Write change records to a CSV file.

    Columns: filename, timestamp, field_type, field_name, trace_index,
             before_value, after_value
    """
    output_path = str(output_path)

    if not changes:
        df = pd.DataFrame(columns=[
            "filename", "timestamp", "field_type", "field_name",
            "trace_index", "before_value", "after_value",
        ])
    else:
        df = pd.DataFrame([asdict(c) for c in changes])

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def append_changelog_csv(
    changes: list[ChangeRecord],
    output_path: str | Path,
) -> str:
    """Append change records to an existing CSV file."""
    output_path = str(output_path)
    path = Path(output_path)

    if not changes:
        return output_path

    new_df = pd.DataFrame([asdict(c) for c in changes])

    if path.exists():
        existing_df = pd.read_csv(output_path, encoding="utf-8-sig")
        df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        df = new_df

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path
