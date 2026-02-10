"""Internationalization (i18n) support for GUI strings.

Usage::

    from segy_toolbox.gui.i18n import tr
    label.setText(tr("open_file"))

Translations are stored as simple dictionaries.  The active locale
is set once via :func:`set_locale` and ``tr()`` returns the
translation for the active locale, falling back to English.
"""

from __future__ import annotations

from typing import Dict

# Type alias for a translation table: key -> translated text
_TranslationTable = Dict[str, str]

# ==================================================================
# Translation tables
# ==================================================================

_EN: _TranslationTable = {
    # File panel
    "open_file": "Open File",
    "open_folder": "Open Folder",
    "select_file": "Select a file",
    "n_files_loaded": "{n} file(s) loaded",
    "remove_selected": "Remove Selected",
    "clear_all": "Clear All",
    "no_segy_found": "No SEG-Y files found",

    # Batch panel
    "batch_options": "Batch Options",
    "output_mode": "Output Mode:",
    "output_separate": "Save to separate folder",
    "output_inplace": "In-place (create backup)",
    "output_dir": "Output Folder:",
    "browse": "Browse",
    "dry_run": "Dry Run (preview only, no actual changes)",
    "batch_start_hint": "Configure options above, then click 'Apply' in the sidebar.",
    "processing_file": "Processing file {current}/{total}...",
    "batch_done": "Done: {success} success, {fail} fail, {skip} skipped (total {total} files)",
    "batch_start": "Configure batch options.",
    "export_report_excel": "Export Report (Excel)",

    # Batch output mode warnings
    "warn_inplace": "Original files will be modified. Backup files (.bak) created in the same location.",
    "info_separate": "Original files are not modified. Copies are created in the output folder.",

    # Overview panel
    "overview_welcome": "Select a SEG-Y file to view metadata.\n\nOpen a file or folder from the left panel.",

    # EBCDIC panel
    "load_template": "Load Template",
    "reset_original": "Restore Original",

    # Binary panel
    "binary_edit_info": "Edit the 'New Value' column to modify fields. Modified fields are highlighted in blue.",

    # Validation panel
    "run_validation": "Run validation",
    "export_validation": "Export Validation Report (Excel)",

    # Log panel
    "export_csv": "Export CSV",
    "export_excel": "Export Excel",
    "clear_log": "Clear Log",

    # Trace panel / Inspector
    "field_inspector": "Field Inspector",
    "inspector_desc": (
        "Trace header statistics for the current file.\n"
        "Click a row to auto-set the Target or Source Field below."
    ),
    "click_action": "Click action:",
    "click_to_target": "Click -> Target",
    "click_to_source": "Click -> Source",
    "no_data_hint": "Load a file to display trace header statistics.",

    # Trace panel / Edit Builder
    "edit_builder": "Edit Builder",
    "validate_expr": "Validate Expression",
    "add_to_queue": "Add to Queue",
    "select_target_field": "Please select a target field",
    "enter_integer": "Please enter an integer value",
    "enter_expression": "Please enter an expression",
    "select_csv": "Please select a CSV file",
    "example_csv_created": "Example CSV created: {name}",
    "csv_create_failed": "CSV creation failed: {error}",
    "target_field_set": "Target Field set: {name}",
    "source_field_set": "Source Field set: {name}",
    "preview_default": "Select a target field to see current value range and predicted results.",

    # Trace panel / Edit Queue
    "edit_queue": "Edit Queue",
    "remove": "Remove",

    # Common
    "condition": "Condition:",
    "value": "Value:",
    "expression": "Expression:",
    "csv_file": "CSV File:",
    "csv_column": "CSV Column:",
    "mode": "Mode:",
    "target_field": "Target Field:",
    "source_field": "Source Field:",
}

_KO: _TranslationTable = {
    # File panel
    "open_file": "\ud30c\uc77c \uc5f4\uae30",
    "open_folder": "\ud3f4\ub354 \uc5f4\uae30",
    "select_file": "\ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694",
    "n_files_loaded": "{n}\uac1c \ud30c\uc77c \ub85c\ub4dc\ub428",
    "remove_selected": "\uc120\ud0dd \ud30c\uc77c \uc81c\uac70",
    "clear_all": "\uc804\uccb4 \ucd08\uae30\ud654",
    "no_segy_found": "SEG-Y \ud30c\uc77c\uc744 \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4",

    # Batch panel
    "batch_options": "\ubc30\uce58 \uc635\uc158",
    "output_mode": "\ucd9c\ub825 \ubaa8\ub4dc:",
    "output_separate": "\ubcc4\ub3c4 \ud3f4\ub354\uc5d0 \uc800\uc7a5",
    "output_inplace": "\uc6d0\ubcf8 \uc704\uce58 (\ubc31\uc5c5 \uc0dd\uc131)",
    "output_dir": "\ucd9c\ub825 \ud3f4\ub354:",
    "browse": "\ucc3e\uc544\ubcf4\uae30",
    "dry_run": "Dry Run (\ubbf8\ub9ac\ubcf4\uae30\ub9cc, \uc2e4\uc81c \uc218\uc815 \uc5c6\uc74c)",
    "batch_start_hint": "\uc704 \uc635\uc158\uc744 \uc124\uc815\ud55c \ud6c4 \uc0ac\uc774\ub4dc\ubc14\uc758 '\uc218\uc815 \uc801\uc6a9' \ubc84\ud2bc\uc744 \ud074\ub9ad\ud558\uc138\uc694.",
    "processing_file": "\ud30c\uc77c {current}/{total} \ucc98\ub9ac \uc911...",
    "batch_done": "\uc644\ub8cc: {success} \uc131\uacf5, {fail} \uc2e4\ud328, {skip} \uac74\ub108\ub700 (\ucd1d {total} \ud30c\uc77c)",
    "batch_start": "\ubc30\uce58 \uc791\uc5c5\uc744 \uc2dc\uc791\ud558\ub824\uba74 \uc635\uc158\uc744 \uc124\uc815\ud558\uc138\uc694.",
    "export_report_excel": "\ub9ac\ud3ec\ud2b8 \ub0b4\ubcf4\ub0b4\uae30 (Excel)",

    # Batch output mode warnings
    "warn_inplace": "\u26a0 \uc6d0\ubcf8 \ud30c\uc77c\uc774 \uc9c1\uc811 \uc218\uc815\ub429\ub2c8\ub2e4. \ubc31\uc5c5 \ud30c\uc77c(.bak)\uc774 \uac19\uc740 \uc704\uce58\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4.",
    "info_separate": "\u2713 \uc6d0\ubcf8 \ud30c\uc77c\uc740 \ubcc0\uacbd\ub418\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \ubcf5\uc0ac\ubcf8\uc774 \ucd9c\ub825 \ud3f4\ub354\uc5d0 \uc0dd\uc131\ub429\ub2c8\ub2e4.",

    # Overview panel
    "overview_welcome": "SEG-Y \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uba74 \uba54\ud0c0\ub370\uc774\ud130\uac00 \uc5ec\uae30\uc5d0 \ud45c\uc2dc\ub429\ub2c8\ub2e4.\n\n\uc67c\ucabd \ud328\ub110\uc5d0\uc11c \ud30c\uc77c\uc744 \uc5f4\uac70\ub098 \ud3f4\ub354\ub97c \uc120\ud0dd\ud558\uc138\uc694.",

    # EBCDIC panel
    "load_template": "\ud15c\ud50c\ub9bf \ub85c\ub4dc",
    "reset_original": "\uc6d0\ubcf8 \ubcf5\uc6d0",

    # Binary panel
    "binary_edit_info": "\uac12\uc744 \uc218\uc815\ud558\ub824\uba74 'New Value' \uc5f4\uc744 \uc9c1\uc811 \ud3b8\uc9d1\ud558\uc138\uc694. \uc218\uc815\ub41c \ud544\ub4dc\ub294 \ud30c\ub780\uc0c9\uc73c\ub85c \ud45c\uc2dc\ub429\ub2c8\ub2e4.",

    # Validation panel
    "run_validation": "\uac80\uc99d\uc744 \uc2e4\ud589\ud558\uc138\uc694",
    "export_validation": "\uac80\uc99d \ub9ac\ud3ec\ud2b8 \ub0b4\ubcf4\ub0b4\uae30 (Excel)",

    # Log panel
    "export_csv": "CSV \ub0b4\ubcf4\ub0b4\uae30",
    "export_excel": "Excel \ub0b4\ubcf4\ub0b4\uae30",
    "clear_log": "\ub85c\uadf8 \uc9c0\uc6b0\uae30",

    # Trace panel / Inspector
    "field_inspector": "Field Inspector",
    "inspector_desc": (
        "\ud604\uc7ac \ud30c\uc77c\uc758 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uc785\ub2c8\ub2e4.\n"
        "\ud589\uc744 \ud074\ub9ad\ud558\uba74 \uc544\ub798 \uc120\ud0dd\ub41c \ubaa8\ub4dc\uc5d0 \ub530\ub77c "
        "Target \ub610\ub294 Source Field\uac00 \uc790\ub3d9 \uc124\uc815\ub429\ub2c8\ub2e4."
    ),
    "click_action": "\ud074\ub9ad \ub3d9\uc791:",
    "click_to_target": "\ud074\ub9ad \u2192 Target",
    "click_to_source": "\ud074\ub9ad \u2192 Source",
    "no_data_hint": "\ud30c\uc77c\uc744 \ub85c\ub4dc\ud558\uba74 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",

    # Trace panel / Edit Builder
    "edit_builder": "Edit Builder",
    "validate_expr": "\uc218\uc2dd \uac80\uc99d",
    "add_to_queue": "\uc791\uc5c5 \ud050\uc5d0 \ucd94\uac00",
    "select_target_field": "Target field\ub97c \uc120\ud0dd\ud558\uc138\uc694",
    "enter_integer": "\uc815\uc218 \uac12\uc744 \uc785\ub825\ud558\uc138\uc694",
    "enter_expression": "\uc218\uc2dd\uc744 \uc785\ub825\ud558\uc138\uc694",
    "select_csv": "CSV \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694",
    "example_csv_created": "\uc608\uc2dc CSV \uc0dd\uc131 \uc644\ub8cc: {name}",
    "csv_create_failed": "CSV \uc0dd\uc131 \uc2e4\ud328: {error}",
    "target_field_set": "Target Field \uc124\uc815: {name}",
    "source_field_set": "Source Field \uc124\uc815: {name}",
    "preview_default": "Target \ud544\ub4dc\ub97c \uc120\ud0dd\ud558\uba74 \ud604\uc7ac \uac12 \ubc94\uc704\uc640 \uc218\uc815 \uacb0\uacfc \uc608\uce21\uc774 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",

    # Trace panel / Edit Queue
    "edit_queue": "Edit Queue",
    "remove": "\uc81c\uac70",

    # Common
    "condition": "\uc870\uac74\uc2dd:",
    "value": "\uac12:",
    "expression": "\uc218\uc2dd:",
    "csv_file": "CSV \ud30c\uc77c:",
    "csv_column": "CSV \uc5f4:",
    "mode": "\ubaa8\ub4dc:",
    "target_field": "Target Field:",
    "source_field": "Source Field:",
}

# ==================================================================
# Translation lookup
# ==================================================================

_LOCALES: dict[str, _TranslationTable] = {
    "en": _EN,
    "ko": _KO,
}

_active_locale: str = "ko"


def set_locale(locale: str) -> None:
    """Set the active locale (e.g. ``"ko"`` or ``"en"``)."""
    global _active_locale
    if locale in _LOCALES:
        _active_locale = locale


def get_locale() -> str:
    """Return the active locale key."""
    return _active_locale


def tr(key: str, **kwargs) -> str:
    """Translate *key* using the active locale.

    Keyword arguments are applied via :meth:`str.format` for
    parameterized messages like ``tr("n_files_loaded", n=5)``.

    Falls back to English, then to the raw key.
    """
    table = _LOCALES.get(_active_locale, _EN)
    text = table.get(key) or _EN.get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
