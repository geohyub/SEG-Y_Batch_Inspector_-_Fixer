"""Tests for changelog reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from segy_toolbox.models import ChangeRecord
from segy_toolbox.reporting.changelog import append_changelog_csv, write_changelog_csv


class TestWriteChangelogCsv:
    def test_write_empty(self, tmp_path: Path):
        output = tmp_path / "changelog.csv"
        write_changelog_csv([], str(output))
        assert output.exists()
        df = pd.read_csv(str(output), encoding="utf-8-sig")
        assert len(df) == 0
        assert "filename" in df.columns

    def test_write_with_changes(self, tmp_path: Path):
        changes = [
            ChangeRecord(
                filename="test.segy",
                field_type="binary_header",
                field_name="sample_interval",
                before_value="2000",
                after_value="4000",
            ),
            ChangeRecord(
                filename="test.segy",
                field_type="trace_header",
                field_name="source_x",
                trace_index=0,
                before_value="500000",
                after_value="50000000",
            ),
        ]
        output = tmp_path / "changelog.csv"
        write_changelog_csv(changes, str(output))

        df = pd.read_csv(str(output), encoding="utf-8-sig")
        assert len(df) == 2
        assert df.iloc[0]["field_name"] == "sample_interval"
        assert df.iloc[1]["trace_index"] == 0

    def test_returns_path(self, tmp_path: Path):
        output = tmp_path / "changelog.csv"
        result = write_changelog_csv([], str(output))
        assert result == str(output)


class TestAppendChangelogCsv:
    def test_append_to_existing(self, tmp_path: Path):
        output = tmp_path / "changelog.csv"

        changes1 = [
            ChangeRecord(filename="a.segy", field_type="binary_header",
                         field_name="sample_interval", before_value="2000", after_value="4000"),
        ]
        write_changelog_csv(changes1, str(output))

        changes2 = [
            ChangeRecord(filename="b.segy", field_type="trace_header",
                         field_name="source_x", before_value="0", after_value="100"),
        ]
        append_changelog_csv(changes2, str(output))

        df = pd.read_csv(str(output), encoding="utf-8-sig")
        assert len(df) == 2

    def test_append_to_nonexistent(self, tmp_path: Path):
        output = tmp_path / "new_changelog.csv"
        changes = [
            ChangeRecord(filename="a.segy", field_type="binary_header",
                         field_name="format_code", before_value="1", after_value="5"),
        ]
        append_changelog_csv(changes, str(output))

        df = pd.read_csv(str(output), encoding="utf-8-sig")
        assert len(df) == 1

    def test_append_empty(self, tmp_path: Path):
        output = tmp_path / "changelog.csv"
        result = append_changelog_csv([], str(output))
        assert result == str(output)
        assert not output.exists()
