"""YAML configuration loading for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from segy_toolbox.models import (
    BinaryHeaderEdit,
    EbcdicEdit,
    EditJob,
    TraceHeaderEdit,
)


@dataclass
class EditConfig:
    """Configuration loaded from a YAML file."""

    # Output settings
    output_mode: str = "separate_folder"  # "separate_folder" | "in_place_backup"
    output_dir: str = "./output"
    backup_suffix: str = ".bak"
    dry_run: bool = False

    # Validation settings
    check_file_structure: bool = True
    check_binary_header: bool = True
    check_trace_header: bool = True
    check_coordinate_range: bool = False
    coordinate_bounds: dict[str, float] = field(default_factory=dict)

    # Raw edit definitions (parsed from YAML)
    edits: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> EditConfig:
        """Load configuration from a YAML file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        # Output settings
        config.output_mode = data.get("output_mode", config.output_mode)
        config.output_dir = data.get("output_dir", config.output_dir)
        if data.get("backup") is True:
            config.output_mode = "in_place_backup"
        config.dry_run = data.get("dry_run", config.dry_run)

        # Validation settings
        validations = data.get("validations", {})
        if isinstance(validations, dict):
            config.check_file_structure = validations.get(
                "check_file_structure", config.check_file_structure
            )
            config.check_coordinate_range = validations.get(
                "check_coordinate_range", config.check_coordinate_range
            )
            config.coordinate_bounds = validations.get(
                "coordinate_bounds", config.coordinate_bounds
            )

        # Edits
        config.edits = data.get("edits", [])

        return config

    def build_edit_job(self) -> EditJob:
        """Convert raw YAML edit definitions into typed EditJob."""
        job = EditJob()

        for edit_def in self.edits:
            edit_type = edit_def.get("type", "")

            if edit_type == "ebcdic":
                job.ebcdic_edits.append(self._parse_ebcdic_edit(edit_def))

            elif edit_type == "binary_header":
                for field_def in edit_def.get("fields", []):
                    job.binary_edits.append(self._parse_binary_edit(field_def))

            elif edit_type == "trace_header":
                condition = edit_def.get("condition", "")
                for field_def in edit_def.get("fields", []):
                    edit = self._parse_trace_edit(field_def)
                    if condition:
                        edit.condition = condition
                    job.trace_edits.append(edit)

        return job

    # ------------------------------------------------------------------
    # Parse helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ebcdic_edit(edit_def: dict) -> EbcdicEdit:
        mode = edit_def.get("mode", "lines")
        edit = EbcdicEdit(mode=mode)

        if mode == "template":
            edit.template_path = edit_def.get("template", "")
            edit.template_replacements = edit_def.get("replacements", {})
        elif mode == "lines":
            edit.lines = {
                int(k): str(v) for k, v in edit_def.get("lines", {}).items()
            }

        return edit

    @staticmethod
    def _parse_binary_edit(field_def: dict) -> BinaryHeaderEdit:
        edit = BinaryHeaderEdit()
        edit.field_name = field_def.get("name", "")
        edit.value = field_def.get("value", 0)
        edit.dtype = field_def.get("dtype", "int16")

        if "offset" in field_def:
            edit.byte_offset = int(field_def["offset"])

        return edit

    @staticmethod
    def _parse_trace_edit(field_def: dict) -> TraceHeaderEdit:
        edit = TraceHeaderEdit()
        edit.field_name = field_def.get("name", "")
        edit.dtype = field_def.get("dtype", "int32")

        if "offset" in field_def:
            edit.byte_offset = int(field_def["offset"])

        if "expression" in field_def:
            edit.mode = "expression"
            edit.expression = field_def["expression"]
        elif "copy_from" in field_def:
            edit.mode = "copy"
            edit.source_field = field_def["copy_from"]
        elif "csv_file" in field_def:
            edit.mode = "csv_import"
            edit.csv_path = field_def["csv_file"]
            edit.csv_column = field_def.get("csv_column", "")
        else:
            edit.mode = "set"
            edit.value = field_def.get("value", 0)

        return edit


def save_config(config: EditConfig, path: str | Path) -> None:
    """Save configuration to a YAML file."""
    data: dict = {
        "output_mode": config.output_mode,
        "output_dir": config.output_dir,
        "dry_run": config.dry_run,
        "validations": {
            "check_file_structure": config.check_file_structure,
            "check_coordinate_range": config.check_coordinate_range,
            "coordinate_bounds": config.coordinate_bounds,
        },
        "edits": config.edits,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
