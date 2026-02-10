"""SEG-Y file writer with backup and change logging."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import segyio

from segy_toolbox.core.binary_editor import BinaryHeaderEditor
from segy_toolbox.core.ebcdic_editor import EbcdicEditor
from segy_toolbox.core.trace_editor import TraceHeaderEditor
from segy_toolbox.io.ebcdic import decode_textual_header, detect_encoding
from segy_toolbox.models import (
    ChangeRecord,
    EditJob,
    EbcdicEdit,
)


class SegyFileWriter:
    """Write SEG-Y files with backup management and edit application."""

    def __init__(self):
        self._ebcdic_editor = EbcdicEditor()
        self._binary_editor = BinaryHeaderEditor()
        self._trace_editor = TraceHeaderEditor()

    def prepare_output(
        self,
        source_path: str,
        output_mode: str = "separate_folder",
        output_dir: str = "./output",
        backup_suffix: str = ".bak",
    ) -> str:
        """Prepare output file path and create backup/copy.

        Returns the path to the file that will be edited.
        """
        source = Path(source_path)

        if output_mode == "separate_folder":
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / source.name
            shutil.copy2(str(source), str(output_path))
            return str(output_path)

        elif output_mode == "in_place_backup":
            backup_path = source.with_suffix(source.suffix + backup_suffix)
            shutil.copy2(str(source), str(backup_path))
            return str(source)

        else:
            raise ValueError(f"Unknown output mode: {output_mode}")

    def apply_edits(
        self,
        output_path: str,
        job: EditJob,
        filename: str = "",
        on_change: Callable[[ChangeRecord], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[ChangeRecord]:
        """Apply all edits to the output file.

        The file must already exist (from prepare_output).
        Opens in r+ mode for in-place header editing.
        """
        all_changes: list[ChangeRecord] = []
        if not filename:
            filename = Path(output_path).name

        # Apply EBCDIC edits
        if job.ebcdic_edits:
            changes = self._apply_ebcdic_edits(output_path, job.ebcdic_edits, filename)
            all_changes.extend(changes)
            for c in changes:
                if on_change:
                    on_change(c)

        # Apply binary header and trace header edits via segyio
        if job.binary_edits or job.trace_edits:
            f = self._open_rw(output_path)
            try:
                # Binary header edits
                for edit in job.binary_edits:
                    change = self._binary_editor.apply_edit(f, edit, filename)
                    all_changes.append(change)
                    if on_change:
                        on_change(change)

                # Trace header edits
                for edit in job.trace_edits:
                    changes = self._trace_editor.apply_edit(
                        f, edit, filename, on_progress
                    )
                    all_changes.extend(changes)
                    for c in changes:
                        if on_change:
                            on_change(c)
            finally:
                f.close()

        return all_changes

    def dry_run(
        self,
        source_path: str,
        job: EditJob,
    ) -> dict:
        """Preview all changes without writing.

        Returns a dict with preview DataFrames for each edit type.
        """
        import pandas as pd

        result = {
            "ebcdic_preview": [],
            "binary_preview": [],
            "trace_preview": [],
        }

        # EBCDIC preview
        if job.ebcdic_edits:
            with open(source_path, "rb") as fp:
                raw = fp.read(3200)
            current_lines = decode_textual_header(raw)
            for edit in job.ebcdic_edits:
                new_lines, changed_indices = self._ebcdic_editor.preview(
                    current_lines, edit
                )
                result["ebcdic_preview"].append({
                    "changed_lines": changed_indices,
                    "before": [current_lines[i] for i in changed_indices],
                    "after": [new_lines[i] for i in changed_indices],
                })

        # Binary header preview
        if job.binary_edits:
            f = self._open_ro(source_path)
            try:
                from segy_toolbox.io.reader import BINARY_FIELD_MAP
                current = {}
                for name, (enum_val, dtype, offset) in BINARY_FIELD_MAP.items():
                    try:
                        current[name] = int(f.bin[enum_val])
                    except Exception:
                        current[name] = 0

                for edit in job.binary_edits:
                    name, before, after = self._binary_editor.preview_edit(
                        current, edit
                    )
                    result["binary_preview"].append({
                        "field": name,
                        "before": before,
                        "after": after,
                    })
            finally:
                f.close()

        # Trace header preview
        if job.trace_edits:
            f = self._open_ro(source_path)
            try:
                for edit in job.trace_edits:
                    preview_df = self._trace_editor.preview_edit(f, edit)
                    result["trace_preview"].append(preview_df)
            finally:
                f.close()

        return result

    @staticmethod
    def check_output_conflicts(
        source_paths: list[str],
        output_mode: str = "separate_folder",
        output_dir: str = "./output",
        backup_suffix: str = ".bak",
    ) -> list[str]:
        """Check for files that would be overwritten.

        Returns a list of existing file paths that would be overwritten.
        """
        conflicts: list[str] = []
        for src in source_paths:
            source = Path(src)
            if output_mode == "separate_folder":
                target = Path(output_dir) / source.name
                if target.exists():
                    conflicts.append(str(target))
            elif output_mode == "in_place_backup":
                backup = source.with_suffix(source.suffix + backup_suffix)
                if backup.exists():
                    conflicts.append(str(backup))
        return conflicts

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_ebcdic_edits(
        self,
        output_path: str,
        edits: list[EbcdicEdit],
        filename: str,
    ) -> list[ChangeRecord]:
        """Apply EBCDIC edits by reading/writing raw bytes."""
        changes: list[ChangeRecord] = []

        with open(output_path, "rb") as fp:
            raw = fp.read(3200)
        encoding = detect_encoding(raw)
        current_lines = decode_textual_header(raw)

        new_lines = list(current_lines)
        for edit in edits:
            new_lines = self._ebcdic_editor.apply_edit(new_lines, edit)

        # Find changes
        for i in range(40):
            if i < len(current_lines) and i < len(new_lines):
                if current_lines[i] != new_lines[i]:
                    changes.append(ChangeRecord(
                        filename=filename,
                        field_type="ebcdic",
                        field_name=f"line_{i + 1:02d}",
                        trace_index=None,
                        before_value=current_lines[i].rstrip(),
                        after_value=new_lines[i].rstrip(),
                    ))

        # Write encoded bytes
        new_bytes = self._ebcdic_editor.encode(new_lines, encoding)
        with open(output_path, "r+b") as fp:
            fp.seek(0)
            fp.write(new_bytes)

        return changes

    @staticmethod
    def _open_rw(path: str) -> segyio.SegyFile:
        """Open SEG-Y for read-write with fallbacks."""
        strategies = [
            {"strict": False},
            {"strict": False, "ignore_geometry": True},
            {"strict": False, "endian": "little"},
            {"strict": False, "ignore_geometry": True, "endian": "little"},
        ]
        for kwargs in strategies:
            try:
                return segyio.open(path, "r+", **kwargs)
            except Exception:
                continue
        raise RuntimeError(f"Cannot open SEG-Y file for writing: {path}")

    @staticmethod
    def _open_ro(path: str) -> segyio.SegyFile:
        """Open SEG-Y for read-only with fallbacks."""
        strategies = [
            {"strict": False},
            {"strict": False, "ignore_geometry": True},
            {"strict": False, "endian": "little"},
            {"strict": False, "ignore_geometry": True, "endian": "little"},
        ]
        for kwargs in strategies:
            try:
                return segyio.open(path, "r", **kwargs)
            except Exception:
                continue
        raise RuntimeError(f"Cannot open SEG-Y file: {path}")
