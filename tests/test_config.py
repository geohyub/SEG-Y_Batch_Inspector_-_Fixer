"""Tests for YAML configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from segy_toolbox.config import EditConfig, save_config


class TestEditConfigDefaults:
    def test_default_output_mode(self):
        config = EditConfig()
        assert config.output_mode == "separate_folder"

    def test_default_output_dir(self):
        config = EditConfig()
        assert config.output_dir == "./output"

    def test_default_dry_run(self):
        config = EditConfig()
        assert config.dry_run is False


class TestEditConfigLoad:
    def test_load_minimal(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("{}\n", encoding="utf-8")
        config = EditConfig.load(str(cfg_file))
        assert config.output_mode == "separate_folder"

    def test_load_output_settings(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "output_mode: in_place_backup\n"
            "output_dir: /tmp/out\n"
            "dry_run: true\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        assert config.output_mode == "in_place_backup"
        assert config.output_dir == "/tmp/out"
        assert config.dry_run is True

    def test_load_backup_flag(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("backup: true\n", encoding="utf-8")
        config = EditConfig.load(str(cfg_file))
        assert config.output_mode == "in_place_backup"

    def test_load_validations(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "validations:\n"
            "  check_file_structure: false\n"
            "  check_coordinate_range: true\n"
            "  coordinate_bounds:\n"
            "    x_min: 100\n"
            "    x_max: 999\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        assert config.check_file_structure is False
        assert config.check_coordinate_range is True
        assert config.coordinate_bounds["x_min"] == 100

    def test_load_edits(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: binary_header\n"
            "    fields:\n"
            "      - name: sample_interval\n"
            "        value: 4000\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        assert len(config.edits) == 1
        assert config.edits[0]["type"] == "binary_header"


class TestBuildEditJob:
    def test_ebcdic_edit(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: ebcdic\n"
            "    mode: lines\n"
            "    lines:\n"
            "      0: 'C01 NEW HEADER'\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert len(job.ebcdic_edits) == 1
        assert job.ebcdic_edits[0].mode == "lines"
        assert 0 in job.ebcdic_edits[0].lines

    def test_binary_header_edit(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: binary_header\n"
            "    fields:\n"
            "      - name: sample_interval\n"
            "        value: 4000\n"
            "      - name: format_code\n"
            "        value: 5\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert len(job.binary_edits) == 2
        assert job.binary_edits[0].field_name == "sample_interval"
        assert job.binary_edits[0].value == 4000

    def test_trace_header_expression(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: trace_header\n"
            "    condition: 'trace_sequence_line > 5'\n"
            "    fields:\n"
            "      - name: source_x\n"
            "        expression: 'source_x * 100'\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert len(job.trace_edits) == 1
        assert job.trace_edits[0].mode == "expression"
        assert job.trace_edits[0].condition == "trace_sequence_line > 5"

    def test_trace_header_copy(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: trace_header\n"
            "    fields:\n"
            "      - name: cdp_x\n"
            "        copy_from: source_x\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert job.trace_edits[0].mode == "copy"
        assert job.trace_edits[0].source_field == "source_x"

    def test_trace_header_csv_import(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: trace_header\n"
            "    fields:\n"
            "      - name: inline\n"
            "        csv_file: headers.csv\n"
            "        csv_column: inline\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert job.trace_edits[0].mode == "csv_import"
        assert job.trace_edits[0].csv_path == "headers.csv"

    def test_trace_header_set(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "edits:\n"
            "  - type: trace_header\n"
            "    fields:\n"
            "      - name: coordinate_scalar\n"
            "        value: -100\n",
            encoding="utf-8",
        )
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert job.trace_edits[0].mode == "set"
        assert job.trace_edits[0].value == -100

    def test_empty_edits(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("edits: []\n", encoding="utf-8")
        config = EditConfig.load(str(cfg_file))
        job = config.build_edit_job()
        assert len(job.ebcdic_edits) == 0
        assert len(job.binary_edits) == 0
        assert len(job.trace_edits) == 0


class TestSaveConfig:
    def test_roundtrip(self, tmp_path: Path):
        config = EditConfig()
        config.output_mode = "in_place_backup"
        config.dry_run = True

        cfg_file = tmp_path / "saved.yaml"
        save_config(config, str(cfg_file))

        loaded = EditConfig.load(str(cfg_file))
        assert loaded.dry_run is True
