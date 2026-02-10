"""Binary file header editor for SEG-Y files."""

from __future__ import annotations

import segyio

from segy_toolbox.io.reader import BINARY_FIELD_MAP
from segy_toolbox.models import BinaryHeaderEdit, ChangeRecord


class BinaryHeaderEditor:
    """Edit the 400-byte binary file header of a SEG-Y file."""

    def resolve_field(self, edit: BinaryHeaderEdit) -> int:
        """Resolve a BinaryHeaderEdit to a segyio BinField enum value.

        Accepts either field_name (e.g., 'sample_interval') or
        byte_offset (e.g., 3217).
        """
        if edit.field_name and edit.field_name in BINARY_FIELD_MAP:
            return BINARY_FIELD_MAP[edit.field_name][0]

        if edit.byte_offset is not None:
            # Map byte offset to segyio BinField
            for name, (enum_val, dtype, offset) in BINARY_FIELD_MAP.items():
                if offset == edit.byte_offset:
                    return enum_val
            # segyio uses 1-based byte offsets within the 400-byte header
            return edit.byte_offset

        raise ValueError(
            f"Cannot resolve binary header field: "
            f"name='{edit.field_name}', offset={edit.byte_offset}"
        )

    def get_display_name(self, edit: BinaryHeaderEdit) -> str:
        """Get a human-readable name for the field."""
        if edit.field_name:
            return edit.field_name
        if edit.byte_offset is not None:
            # Look up by offset
            for name, (_, _, offset) in BINARY_FIELD_MAP.items():
                if offset == edit.byte_offset:
                    return f"{name} (byte {offset})"
            return f"byte_offset_{edit.byte_offset}"
        return "unknown"

    def apply_edit(
        self,
        f: segyio.SegyFile,
        edit: BinaryHeaderEdit,
        filename: str = "",
    ) -> ChangeRecord:
        """Apply a single binary header edit and return a change record."""
        bin_field = self.resolve_field(edit)
        display_name = self.get_display_name(edit)

        # Read current value
        try:
            before_value = f.bin[bin_field]
        except Exception:
            before_value = 0

        # Write new value
        f.bin[bin_field] = int(edit.value)

        return ChangeRecord(
            filename=filename,
            field_type="binary_header",
            field_name=display_name,
            trace_index=None,
            before_value=str(before_value),
            after_value=str(int(edit.value)),
        )

    def preview_edit(
        self,
        current_values: dict[str, int],
        edit: BinaryHeaderEdit,
    ) -> tuple[str, int, int]:
        """Preview a binary header edit without applying.

        Returns (field_name, current_value, new_value).
        """
        display_name = self.get_display_name(edit)
        current = current_values.get(
            edit.field_name, current_values.get(display_name, 0)
        )
        return display_name, current, int(edit.value)

    @staticmethod
    def get_all_fields() -> list[dict[str, str]]:
        """Return list of all known binary header fields for GUI display."""
        fields = []
        for name, (enum_val, dtype, offset) in BINARY_FIELD_MAP.items():
            fields.append({
                "name": name,
                "dtype": dtype,
                "byte_offset": str(offset),
                "description": name.replace("_", " ").title(),
            })
        return fields
