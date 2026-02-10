"""Tests for the SEG-Y validation engine."""

from __future__ import annotations

import pytest

from segy_toolbox.core.validator import SegyValidator
from segy_toolbox.models import SegyFileInfo, ValidationCheck


class TestStructuralValidation:
    def setup_method(self):
        self.validator = SegyValidator()

    def test_valid_file(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        assert result.overall_status in ("PASS", "WARNING")

    def test_file_size_mismatch(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=5000,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        fail_checks = [c for c in result.checks if c.status == "FAIL"]
        assert any("File Size" in c.name for c in fail_checks)

    def test_zero_trace_count(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=3600,
            trace_count=0,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=0,
        )
        result = self.validator.validate(info)
        fail_checks = [c for c in result.checks if c.status == "FAIL"]
        assert any("Trace Count" in c.name for c in fail_checks)

    def test_too_small_file(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=100,
            trace_count=0,
            expected_file_size=0,
        )
        result = self.validator.validate(info)
        fail_checks = [c for c in result.checks if c.status == "FAIL"]
        assert any("Minimum" in c.name for c in fail_checks)


class TestBinaryHeaderValidation:
    def setup_method(self):
        self.validator = SegyValidator()

    def test_valid_headers(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        pass_checks = [c for c in result.checks if c.category == "binary_header" and c.status == "PASS"]
        assert len(pass_checks) >= 2  # sample_interval + samples_per_trace + format_code

    def test_invalid_sample_interval(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=0,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        fail_checks = [c for c in result.checks if c.status == "FAIL"]
        assert any("Sample Interval" in c.name for c in fail_checks)

    def test_invalid_format_code(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=99,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        fail_checks = [c for c in result.checks if c.status == "FAIL"]
        assert any("Format" in c.name for c in fail_checks)

    def test_high_samples_warning(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=200000,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        warn_checks = [c for c in result.checks if c.status == "WARNING"]
        assert any("Samples" in c.name for c in warn_checks)


class TestTraceHeaderValidation:
    def setup_method(self):
        self.validator = SegyValidator()

    def test_consistent_scalar(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
            trace_header_summary={
                "coordinate_scalar": {"min": -100, "max": -100, "mean": -100, "std": 0},
                "source_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "source_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
                "cdp_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "cdp_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
            },
        )
        result = self.validator.validate(info)
        pass_checks = [c for c in result.checks if c.name == "Coordinate Scalar Consistency"]
        assert len(pass_checks) == 1
        assert pass_checks[0].status == "PASS"

    def test_varying_scalar_warning(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
            trace_header_summary={
                "coordinate_scalar": {"min": -100, "max": -1, "mean": -50, "std": 49},
            },
        )
        result = self.validator.validate(info)
        warn = [c for c in result.checks if c.name == "Coordinate Scalar Consistency"]
        assert len(warn) == 1
        assert warn[0].status == "WARNING"

    def test_all_zeros_warning(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
            trace_header_summary={
                "coordinate_scalar": {"min": 0, "max": 0, "mean": 0, "std": 0},
                "source_x": {"min": 0, "max": 0, "mean": 0, "std": 0},
                "source_y": {"min": 0, "max": 0, "mean": 0, "std": 0},
                "cdp_x": {"min": 0, "max": 0, "mean": 0, "std": 0},
                "cdp_y": {"min": 0, "max": 0, "mean": 0, "std": 0},
            },
        )
        result = self.validator.validate(info)
        warn = [c for c in result.checks if c.status == "WARNING" and "all zeros" in c.message]
        assert len(warn) >= 1


class TestOverallStatus:
    def setup_method(self):
        self.validator = SegyValidator()

    def test_all_pass(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
            trace_header_summary={
                "coordinate_scalar": {"min": -100, "max": -100, "mean": -100, "std": 0},
                "source_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "source_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
                "cdp_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "cdp_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
            },
        )
        result = self.validator.validate(info)
        assert result.overall_status == "PASS"

    def test_fail_overrides_warning(self):
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=5000,
            trace_count=0,
            samples_per_trace=0,
            sample_interval=0,
            format_code=99,
            expected_file_size=7200,
        )
        result = self.validator.validate(info)
        assert result.overall_status == "FAIL"


class TestCoordinateBoundsValidation:
    def test_within_bounds(self):
        validator = SegyValidator(
            coordinate_bounds={"x_min": 0, "x_max": 1000000, "y_min": 0, "y_max": 9000000},
            check_coordinate_range=True,
        )
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
            coordinate_scalar=1,
            trace_header_summary={
                "coordinate_scalar": {"min": 1, "max": 1, "mean": 1, "std": 0},
                "source_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "source_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
                "cdp_x": {"min": 500000, "max": 501000, "mean": 500500, "std": 300},
                "cdp_y": {"min": 6000000, "max": 6001000, "mean": 6000500, "std": 300},
            },
        )
        result = validator.validate(info)
        bound_warns = [c for c in result.checks if "Bounds" in c.name and c.status == "WARNING"]
        assert len(bound_warns) == 0


class TestDisabledChecks:
    def test_skip_structure(self):
        validator = SegyValidator(check_structure=False)
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=100,
            trace_count=0,
        )
        result = validator.validate(info)
        struct_checks = [c for c in result.checks if c.category == "structure"]
        assert len(struct_checks) == 0

    def test_skip_binary(self):
        validator = SegyValidator(check_binary_header=False)
        info = SegyFileInfo(
            filename="test.segy",
            file_size_bytes=7200,
            trace_count=10,
            samples_per_trace=100,
            sample_interval=2000,
            format_code=1,
            bytes_per_sample=4,
            expected_file_size=7200,
        )
        result = validator.validate(info)
        binary_checks = [c for c in result.checks if c.category == "binary_header"]
        assert len(binary_checks) == 0
