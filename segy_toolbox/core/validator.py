"""Integrity validation engine for SEG-Y files."""

from __future__ import annotations

import numpy as np

from segy_toolbox.models import (
    FORMAT_BPS,
    SegyFileInfo,
    ValidationCheck,
    ValidationResult,
)


class SegyValidator:
    """Run pre-edit and post-edit validation checks on SEG-Y files."""

    def __init__(
        self,
        coordinate_bounds: dict[str, float] | None = None,
        check_structure: bool = True,
        check_binary_header: bool = True,
        check_trace_header: bool = True,
        check_coordinate_range: bool = True,
    ):
        self.coordinate_bounds = coordinate_bounds
        self._check_structure = check_structure
        self._check_binary = check_binary_header
        self._check_trace = check_trace_header
        self._check_coords = check_coordinate_range

    def validate(self, info: SegyFileInfo) -> ValidationResult:
        """Run all configured validation checks."""
        checks: list[ValidationCheck] = []

        if self._check_structure:
            checks.extend(self._validate_structure(info))

        if self._check_binary:
            checks.extend(self._validate_binary_header(info))

        if self._check_trace:
            checks.extend(self._validate_trace_headers(info))

        if self._check_coords and self.coordinate_bounds:
            checks.extend(self._validate_coordinate_range(info))

        # Determine overall status
        if any(c.status == "FAIL" for c in checks):
            overall = "FAIL"
        elif any(c.status == "WARNING" for c in checks):
            overall = "WARNING"
        else:
            overall = "PASS"

        return ValidationResult(
            filename=info.filename,
            overall_status=overall,
            checks=checks,
        )

    def validate_post_edit(
        self,
        before: SegyFileInfo,
        after: SegyFileInfo,
        edited_fields: set[str] | None = None,
    ) -> ValidationResult:
        """Post-edit validation: check only intended fields changed."""
        checks: list[ValidationCheck] = []

        # Re-run structural validation on the edited file
        checks.extend(self._validate_structure(after))
        checks.extend(self._validate_binary_header(after))

        # Diff check: binary header fields that should NOT have changed
        if edited_fields:
            for field_name, before_val in before.binary_header.items():
                after_val = after.binary_header.get(field_name, before_val)
                if field_name not in edited_fields and before_val != after_val:
                    checks.append(ValidationCheck(
                        name=f"Unintended Change: {field_name}",
                        category="post_edit",
                        status="WARNING",
                        message=f"Binary header '{field_name}' changed unexpectedly",
                        details=f"Before: {before_val}, After: {after_val}",
                    ))

        if any(c.status == "FAIL" for c in checks):
            overall = "FAIL"
        elif any(c.status == "WARNING" for c in checks):
            overall = "WARNING"
        else:
            overall = "PASS"

        return ValidationResult(
            filename=after.filename,
            overall_status=overall,
            checks=checks,
        )

    # ------------------------------------------------------------------
    # Structural checks
    # ------------------------------------------------------------------

    def _validate_structure(self, info: SegyFileInfo) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []

        # File size consistency
        if info.expected_file_size > 0:
            if info.file_size_bytes == info.expected_file_size:
                checks.append(ValidationCheck(
                    name="File Size Consistency",
                    category="structure",
                    status="PASS",
                    message=(
                        f"File size matches expected: "
                        f"{info.file_size_bytes:,} bytes"
                    ),
                ))
            else:
                diff = info.file_size_bytes - info.expected_file_size
                checks.append(ValidationCheck(
                    name="File Size Consistency",
                    category="structure",
                    status="FAIL",
                    message="File size does not match expected structure",
                    details=(
                        f"Actual: {info.file_size_bytes:,} bytes, "
                        f"Expected: {info.expected_file_size:,} bytes, "
                        f"Difference: {diff:+,} bytes\n"
                        f"Formula: 3200 + 400 + (240 + {info.samples_per_trace} x "
                        f"{info.bytes_per_sample}) x {info.trace_count}"
                    ),
                ))
        else:
            checks.append(ValidationCheck(
                name="File Size Consistency",
                category="structure",
                status="WARNING",
                message="Cannot verify file size (missing header info)",
            ))

        # Minimum file size
        if info.file_size_bytes < 3600:
            checks.append(ValidationCheck(
                name="Minimum File Size",
                category="structure",
                status="FAIL",
                message=(
                    f"File too small: {info.file_size_bytes} bytes "
                    f"(minimum 3600 for header)"
                ),
            ))

        # Trace count > 0
        if info.trace_count <= 0:
            checks.append(ValidationCheck(
                name="Trace Count",
                category="structure",
                status="FAIL",
                message=f"Invalid trace count: {info.trace_count}",
            ))
        else:
            checks.append(ValidationCheck(
                name="Trace Count",
                category="structure",
                status="PASS",
                message=f"Trace count: {info.trace_count:,}",
            ))

        return checks

    # ------------------------------------------------------------------
    # Binary header checks
    # ------------------------------------------------------------------

    def _validate_binary_header(self, info: SegyFileInfo) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []

        # Sample interval
        if info.sample_interval <= 0:
            checks.append(ValidationCheck(
                name="Sample Interval",
                category="binary_header",
                status="FAIL",
                message=f"Invalid sample interval: {info.sample_interval} us",
            ))
        else:
            checks.append(ValidationCheck(
                name="Sample Interval",
                category="binary_header",
                status="PASS",
                message=f"Sample interval: {info.sample_interval} us",
            ))

        # Samples per trace
        if info.samples_per_trace <= 0:
            checks.append(ValidationCheck(
                name="Samples per Trace",
                category="binary_header",
                status="FAIL",
                message=f"Invalid samples per trace: {info.samples_per_trace}",
            ))
        elif info.samples_per_trace > 100000:
            checks.append(ValidationCheck(
                name="Samples per Trace",
                category="binary_header",
                status="WARNING",
                message=f"Unusually high samples per trace: {info.samples_per_trace}",
            ))
        else:
            checks.append(ValidationCheck(
                name="Samples per Trace",
                category="binary_header",
                status="PASS",
                message=f"Samples per trace: {info.samples_per_trace}",
            ))

        # Format code
        valid_formats = set(FORMAT_BPS.keys())
        if info.format_code not in valid_formats:
            checks.append(ValidationCheck(
                name="Data Format Code",
                category="binary_header",
                status="FAIL",
                message=f"Unknown format code: {info.format_code}",
                details=f"Valid codes: {sorted(valid_formats)}",
            ))
        else:
            checks.append(ValidationCheck(
                name="Data Format Code",
                category="binary_header",
                status="PASS",
                message=f"Format code: {info.format_code} ({FORMAT_BPS[info.format_code]} bytes/sample)",
            ))

        return checks

    # ------------------------------------------------------------------
    # Trace header checks
    # ------------------------------------------------------------------

    def _validate_trace_headers(self, info: SegyFileInfo) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []

        # Coordinate scalar consistency
        scalar_stats = info.trace_header_summary.get("coordinate_scalar", {})
        scalar_min = scalar_stats.get("min", 0)
        scalar_max = scalar_stats.get("max", 0)
        if scalar_min != scalar_max:
            checks.append(ValidationCheck(
                name="Coordinate Scalar Consistency",
                category="trace_header",
                status="WARNING",
                message="Coordinate scalar varies across traces",
                details=f"Min: {scalar_min}, Max: {scalar_max}",
            ))
        else:
            checks.append(ValidationCheck(
                name="Coordinate Scalar Consistency",
                category="trace_header",
                status="PASS",
                message=f"Coordinate scalar: {scalar_min} (consistent)",
            ))

        # Coordinate outlier detection (3-sigma)
        for coord_name in ["source_x", "source_y", "cdp_x", "cdp_y"]:
            stats = info.trace_header_summary.get(coord_name, {})
            mean_val = stats.get("mean", 0)
            std_val = stats.get("std", 0)
            min_val = stats.get("min", 0)
            max_val = stats.get("max", 0)

            if std_val > 0 and mean_val != 0:
                range_ratio = (max_val - min_val) / abs(mean_val) if mean_val != 0 else 0
                if range_ratio > 1.0:
                    checks.append(ValidationCheck(
                        name=f"Coordinate Range: {coord_name}",
                        category="trace_header",
                        status="WARNING",
                        message=f"{coord_name} has high variability",
                        details=(
                            f"Min: {min_val:.0f}, Max: {max_val:.0f}, "
                            f"Mean: {mean_val:.0f}, Std: {std_val:.0f}"
                        ),
                    ))
                else:
                    checks.append(ValidationCheck(
                        name=f"Coordinate Range: {coord_name}",
                        category="trace_header",
                        status="PASS",
                        message=f"{coord_name}: {min_val:.0f} ~ {max_val:.0f}",
                    ))
            elif all(v == 0 for v in [min_val, max_val, mean_val]):
                checks.append(ValidationCheck(
                    name=f"Coordinate Range: {coord_name}",
                    category="trace_header",
                    status="WARNING",
                    message=f"{coord_name}: all zeros",
                ))

        return checks

    # ------------------------------------------------------------------
    # Coordinate bounds check
    # ------------------------------------------------------------------

    def _validate_coordinate_range(self, info: SegyFileInfo) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        bounds = self.coordinate_bounds or {}

        coord_mapping = {
            "source_x": ("x_min", "x_max"),
            "source_y": ("y_min", "y_max"),
            "cdp_x": ("x_min", "x_max"),
            "cdp_y": ("y_min", "y_max"),
        }

        scalar = info.coordinate_scalar
        scale_factor = 1.0
        if scalar < 0:
            scale_factor = 1.0 / abs(scalar)
        elif scalar > 0:
            scale_factor = float(scalar)

        for field_name, (min_key, max_key) in coord_mapping.items():
            stats = info.trace_header_summary.get(field_name, {})
            field_min = stats.get("min", 0) * scale_factor
            field_max = stats.get("max", 0) * scale_factor

            if field_min == 0 and field_max == 0:
                continue

            bound_min = bounds.get(min_key)
            bound_max = bounds.get(max_key)

            if bound_min is not None and field_min < bound_min:
                checks.append(ValidationCheck(
                    name=f"Bounds Check: {field_name}",
                    category="trace_header",
                    status="WARNING",
                    message=f"{field_name} min ({field_min:.0f}) below bound ({bound_min})",
                ))
            if bound_max is not None and field_max > bound_max:
                checks.append(ValidationCheck(
                    name=f"Bounds Check: {field_name}",
                    category="trace_header",
                    status="WARNING",
                    message=f"{field_name} max ({field_max:.0f}) above bound ({bound_max})",
                ))

        return checks
