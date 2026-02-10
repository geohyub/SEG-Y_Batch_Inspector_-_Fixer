"""Trace header batch editor for SEG-Y files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import segyio

from segy_toolbox.core.expression import SafeEvaluator, validate_expression
from segy_toolbox.io.reader import TRACE_FIELD_MAP
from segy_toolbox.models import ChangeRecord, TraceHeaderEdit


class TraceHeaderEditor:
    """Batch edit trace headers with expressions, conditions, and CSV import."""

    def resolve_field(self, edit: TraceHeaderEdit) -> int:
        """Resolve field name or byte offset to segyio TraceField enum."""
        if edit.field_name and edit.field_name in TRACE_FIELD_MAP:
            return TRACE_FIELD_MAP[edit.field_name][0]

        if edit.byte_offset is not None:
            for name, (enum_val, dtype, offset) in TRACE_FIELD_MAP.items():
                if offset == edit.byte_offset:
                    return enum_val
            return edit.byte_offset

        raise ValueError(
            f"Cannot resolve trace header field: "
            f"name='{edit.field_name}', offset={edit.byte_offset}"
        )

    def get_display_name(self, edit: TraceHeaderEdit) -> str:
        """Get a human-readable name for the field."""
        if edit.field_name and edit.field_name in TRACE_FIELD_MAP:
            return edit.field_name
        if edit.byte_offset is not None:
            for name, (_, _, offset) in TRACE_FIELD_MAP.items():
                if offset == edit.byte_offset:
                    return f"{name} (byte {offset})"
            return f"byte_offset_{edit.byte_offset}"
        return edit.field_name or "unknown"

    def apply_edit(
        self,
        f: segyio.SegyFile,
        edit: TraceHeaderEdit,
        filename: str = "",
        on_progress: callable = None,
    ) -> list[ChangeRecord]:
        """Apply a trace header edit to all matching traces."""
        target_field = self.resolve_field(edit)
        display_name = self.get_display_name(edit)
        changes: list[ChangeRecord] = []
        ntraces = f.tracecount
        errors: list[str] = []

        # Load CSV data if csv_import mode
        csv_data = None
        if edit.mode == "csv_import" and edit.csv_path:
            csv_data = self._load_csv(edit.csv_path)

        # Load source field values if copy mode
        source_values = None
        if edit.mode == "copy" and edit.source_field:
            source_enum = self._resolve_source_field(edit.source_field)
            raw = f.attributes(source_enum)[:]
            # Convert numpy array to Python int list for safety
            source_values = [int(v) for v in raw]

        for i in range(ntraces):
            if on_progress and i % 500 == 0:
                on_progress(i, ntraces)

            try:
                header = f.header[i]

                # Check condition
                if edit.condition and not self._evaluate_condition(edit.condition, header, i):
                    continue

                before_value = int(header[target_field])

                # Compute new value based on mode
                if edit.mode == "set":
                    new_value = int(edit.value)

                elif edit.mode == "expression":
                    new_value = self._evaluate_expression(
                        edit.expression, header, i
                    )

                elif edit.mode == "copy":
                    if source_values is not None:
                        new_value = source_values[i]
                    else:
                        new_value = before_value

                elif edit.mode == "csv_import":
                    if csv_data is not None and i < len(csv_data):
                        col = edit.csv_column or edit.field_name
                        if col in csv_data.columns:
                            new_value = int(csv_data.iloc[i][col])
                        else:
                            continue
                    else:
                        continue
                else:
                    continue

                if new_value != before_value:
                    header[target_field] = int(new_value)
                    # Only log sampled changes to avoid huge logs
                    if len(changes) < 10000 or i % 100 == 0:
                        changes.append(ChangeRecord(
                            filename=filename,
                            field_type="trace_header",
                            field_name=display_name,
                            trace_index=i,
                            before_value=str(before_value),
                            after_value=str(new_value),
                        ))

            except Exception as e:
                if len(errors) < 10:
                    errors.append(f"Trace {i}: {e}")

        # Report progress complete
        if on_progress:
            on_progress(ntraces, ntraces)

        # Flush writes to disk
        try:
            f.flush()
        except Exception:
            pass

        if errors:
            error_msg = "; ".join(errors[:5])
            if len(errors) > 5:
                error_msg += f" ... (+{len(errors) - 5} more)"
            raise RuntimeError(
                f"Errors during trace header edit '{display_name}': {error_msg}"
            )

        return changes

    def preview_edit(
        self,
        f: segyio.SegyFile,
        edit: TraceHeaderEdit,
        max_traces: int = 20,
    ) -> pd.DataFrame:
        """Preview what changes would be applied to the first N traces."""
        target_field = self.resolve_field(edit)
        display_name = self.get_display_name(edit)

        csv_data = None
        if edit.mode == "csv_import" and edit.csv_path:
            csv_data = self._load_csv(edit.csv_path)

        source_values = None
        if edit.mode == "copy" and edit.source_field:
            source_enum = self._resolve_source_field(edit.source_field)
            raw = f.attributes(source_enum)[:]
            source_values = [int(v) for v in raw]

        rows: list[dict] = []
        n = min(max_traces, f.tracecount)

        for i in range(n):
            try:
                header = f.header[i]
                before_value = int(header[target_field])

                # Check condition
                matches_condition = True
                if edit.condition:
                    matches_condition = self._evaluate_condition(
                        edit.condition, header, i
                    )

                if not matches_condition:
                    rows.append({
                        "trace": i,
                        "field": display_name,
                        "current": before_value,
                        "new": before_value,
                        "changed": False,
                        "skipped": True,
                    })
                    continue

                if edit.mode == "set":
                    new_value = int(edit.value)
                elif edit.mode == "expression":
                    new_value = self._evaluate_expression(
                        edit.expression, header, i
                    )
                elif edit.mode == "copy":
                    new_value = source_values[i] if source_values is not None else before_value
                elif edit.mode == "csv_import":
                    if csv_data is not None and i < len(csv_data):
                        col = edit.csv_column or edit.field_name
                        new_value = int(csv_data.iloc[i].get(col, before_value))
                    else:
                        new_value = before_value
                else:
                    new_value = before_value

                rows.append({
                    "trace": i,
                    "field": display_name,
                    "current": before_value,
                    "new": new_value,
                    "changed": new_value != before_value,
                    "skipped": False,
                })
            except Exception:
                rows.append({
                    "trace": i,
                    "field": display_name,
                    "current": 0,
                    "new": 0,
                    "changed": False,
                    "skipped": True,
                })

        return pd.DataFrame(rows)

    def validate_edit(self, edit: TraceHeaderEdit) -> str | None:
        """Validate a trace header edit before applying.

        Returns None if valid, or an error message string.
        """
        # Check field name
        if edit.field_name and edit.field_name not in TRACE_FIELD_MAP:
            if edit.byte_offset is None:
                return f"Unknown field: '{edit.field_name}'"

        available_vars = list(TRACE_FIELD_MAP.keys()) + ["trace_index"]

        # Validate expression
        if edit.mode == "expression" and edit.expression:
            err = validate_expression(edit.expression, available_vars)
            if err:
                return f"Expression error: {err}"

        # Validate condition
        if edit.condition:
            err = validate_expression(edit.condition, available_vars)
            if err:
                return f"Condition error: {err}"

        # Validate CSV path
        if edit.mode == "csv_import" and edit.csv_path:
            if not Path(edit.csv_path).exists():
                return f"CSV file not found: {edit.csv_path}"

        # Validate source field for copy
        if edit.mode == "copy" and edit.source_field:
            if edit.source_field not in TRACE_FIELD_MAP:
                return f"Unknown source field: '{edit.source_field}'"

        return None

    @staticmethod
    def get_all_fields() -> list[dict[str, str]]:
        """Return list of all known trace header fields for GUI display."""
        fields = []
        for name, (enum_val, dtype, offset) in TRACE_FIELD_MAP.items():
            fields.append({
                "name": name,
                "dtype": dtype,
                "byte_offset": str(offset),
                "description": name.replace("_", " ").title(),
            })
        return fields

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_expression(
        self, expression: str, header: dict, trace_index: int
    ) -> int:
        """Evaluate an arithmetic expression against trace header values."""
        variables = self._build_variables(header, trace_index)
        evaluator = SafeEvaluator(variables)
        result = evaluator.evaluate(expression)
        return int(round(result))

    def _evaluate_condition(
        self, condition: str, header: dict, trace_index: int
    ) -> bool:
        """Evaluate a boolean condition against trace header values."""
        variables = self._build_variables(header, trace_index)
        evaluator = SafeEvaluator(variables)
        return evaluator.evaluate_condition(condition)

    @staticmethod
    def _build_variables(header: dict, trace_index: int) -> dict[str, int | float]:
        """Build variable dict from trace header for expression evaluation."""
        variables: dict[str, int | float] = {"trace_index": trace_index}
        for name, (enum_val, dtype, offset) in TRACE_FIELD_MAP.items():
            try:
                variables[name] = header[enum_val]
            except (KeyError, TypeError):
                variables[name] = 0
        return variables

    def _resolve_source_field(self, field_name: str) -> int:
        """Resolve source field name to segyio TraceField enum."""
        if field_name in TRACE_FIELD_MAP:
            return TRACE_FIELD_MAP[field_name][0]
        raise ValueError(f"Unknown source field: '{field_name}'")

    @staticmethod
    def _load_csv(csv_path: str) -> pd.DataFrame:
        """Load CSV file for trace header import."""
        return pd.read_csv(csv_path)
