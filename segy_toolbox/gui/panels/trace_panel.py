"""Trace header batch editor panel with Field Inspector and Sample Preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.core.expression import SafeEvaluator, ExpressionError
from segy_toolbox.core.trace_editor import TraceHeaderEditor
from segy_toolbox.io.reader import TRACE_FIELD_MAP
from segy_toolbox.models import SegyFileInfo, TraceHeaderEdit


_MODES = [
    ("set", "Set Value", "\uace0\uc815 \uac12 \uc124\uc815"),
    ("expression", "Expression", "\uc218\uc2dd \ubcc0\ud658 (\uc608: source_x * 100)"),
    ("copy", "Copy Field", "\ub2e4\ub978 \ud544\ub4dc \uac12 \ubcf5\uc0ac"),
    ("csv_import", "CSV Import", "CSV\uc5d0\uc11c \uac12 \uac00\uc838\uc624\uae30"),
]

# CSV example format shown in the UI
_CSV_EXAMPLE = (
    "CSV \ud30c\uc77c \ud3ec\ub9f7 \uc608\uc2dc:\n"
    "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510\n"
    "\u2502 trace_index \u2502 source_x   \u2502 source_y   \u2502\n"
    "\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524\n"
    "\u2502 0          \u2502 500000     \u2502 6000000    \u2502\n"
    "\u2502 1          \u2502 500100     \u2502 6000050    \u2502\n"
    "\u2502 2          \u2502 500200     \u2502 6000100    \u2502\n"
    "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518\n"
    "\u2022 \uccab \ud589: \uc5f4 \uc774\ub984 (trace_index \ud544\uc218)\n"
    "\u2022 CSV Column: \uc801\uc6a9\ud560 \uc5f4 \uc774\ub984 (\uc608: source_x)"
)

# Inspector field category ordering for logical grouping
_FIELD_CATEGORIES = {
    # Sequence & ID
    "trace_sequence_line": "1_\uc2dc\ud000\uc2a4",
    "trace_sequence_file": "1_\uc2dc\ud000\uc2a4",
    "field_record": "1_\uc2dc\ud000\uc2a4",
    "trace_number": "1_\uc2dc\ud000\uc2a4",
    "energy_source_point": "1_\uc2dc\ud000\uc2a4",
    "trace_id": "1_\uc2dc\ud000\uc2a4",
    # CDP & Ensemble
    "cdp": "2_CDP",
    "cdp_trace": "2_CDP",
    "cdp_x": "2_CDP",
    "cdp_y": "2_CDP",
    "offset": "2_CDP",
    # Source / Receiver coordinates
    "source_x": "3_\uc88c\ud45c",
    "source_y": "3_\uc88c\ud45c",
    "group_x": "3_\uc88c\ud45c",
    "group_y": "3_\uc88c\ud45c",
    "coordinate_scalar": "3_\uc88c\ud45c",
    "coordinate_units": "3_\uc88c\ud45c",
    # Elevation & depth
    "elevation_scalar": "4_\uc9c0\ud45c",
    "receiver_elevation": "4_\uc9c0\ud45c",
    "source_surface_elevation": "4_\uc9c0\ud45c",
    "source_depth": "4_\uc9c0\ud45c",
    "water_depth_source": "4_\uc9c0\ud45c",
    "water_depth_receiver": "4_\uc9c0\ud45c",
    "datum_elevation_receiver": "4_\uc9c0\ud45c",
    "datum_elevation_source": "4_\uc9c0\ud45c",
    # 3D geometry
    "inline": "5_3D",
    "crossline": "5_3D",
    "shotpoint": "5_3D",
    "shotpoint_scalar": "5_3D",
    # Timing & sampling
    "delay_recording_time": "6_\uc2dc\uac04",
    "samples": "6_\uc2dc\uac04",
    "sample_interval": "6_\uc2dc\uac04",
    "mute_time_start": "6_\uc2dc\uac04",
    "mute_time_end": "6_\uc2dc\uac04",
    # Statics
    "source_static": "7_\uc2a4\ud0c0\ud2f1",
    "receiver_static": "7_\uc2a4\ud0c0\ud2f1",
    "total_static": "7_\uc2a4\ud0c0\ud2f1",
}

# Category display labels (strip sort prefix)
_CATEGORY_LABELS = {
    "1_\uc2dc\ud000\uc2a4": "\uc2dc\ud000\uc2a4/ID",
    "2_CDP": "CDP/Ensemble",
    "3_\uc88c\ud45c": "\uc88c\ud45c",
    "4_\uc9c0\ud45c": "\uc9c0\ud45c/\uc218\uc2ec",
    "5_3D": "3D Geometry",
    "6_\uc2dc\uac04": "\uc2dc\uac04/\uc0d8\ud50c\ub9c1",
    "7_\uc2a4\ud0c0\ud2f1": "\uc2a4\ud0c0\ud2f1",
}


class TracePanel(QWidget):
    """Trace header batch editor with field inspector and live preview."""

    # Click mode constants
    _CLICK_TARGET = 0
    _CLICK_SOURCE = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: SegyFileInfo | None = None
        self._edit_queue: list[TraceHeaderEdit] = []
        self._field_names = sorted(TRACE_FIELD_MAP.keys())
        self._click_mode = self._CLICK_TARGET
        self._build_ui()

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        # Main horizontal splitter: [A] Field Inspector | [B+C] Editor
        main_splitter = QSplitter(Qt.Horizontal)

        # --- [A] Field Inspector (left) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        inspector_title = QLabel("Field Inspector")
        inspector_title.setObjectName("sectionLabel")
        left_layout.addWidget(inspector_title)

        inspector_desc = QLabel(
            "\ud604\uc7ac \ud30c\uc77c\uc758 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uc785\ub2c8\ub2e4.\n"
            "\ud589\uc744 \ud074\ub9ad\ud558\uba74 \uc544\ub798 \uc120\ud0dd\ub41c \ubaa8\ub4dc\uc5d0 \ub530\ub77c "
            "Target \ub610\ub294 Source Field\uac00 \uc790\ub3d9 \uc124\uc815\ub429\ub2c8\ub2e4."
        )
        inspector_desc.setObjectName("subtitleLabel")
        inspector_desc.setWordWrap(True)
        left_layout.addWidget(inspector_desc)

        # Click mode toggle: Target / Source
        click_mode_frame = QFrame()
        click_mode_frame.setStyleSheet(
            "QFrame { background: #313244; border-radius: 6px; padding: 4px; }"
        )
        click_mode_layout = QHBoxLayout(click_mode_frame)
        click_mode_layout.setContentsMargins(8, 4, 8, 4)
        click_mode_layout.setSpacing(4)

        click_label = QLabel("\ud074\ub9ad \ub3d9\uc791:")
        click_label.setStyleSheet("color: #bac2de; font-size: 12px;")
        click_mode_layout.addWidget(click_label)

        self._radio_target = QRadioButton("Target Field")
        self._radio_target.setChecked(True)
        self._radio_target.setStyleSheet(
            "QRadioButton { color: #89b4fa; font-weight: bold; font-size: 12px; }"
        )
        self._radio_target.toggled.connect(self._on_click_mode_toggled)

        self._radio_source = QRadioButton("Source Field")
        self._radio_source.setStyleSheet(
            "QRadioButton { color: #f9e2af; font-weight: bold; font-size: 12px; }"
        )

        self._click_mode_group = QButtonGroup(self)
        self._click_mode_group.addButton(self._radio_target, self._CLICK_TARGET)
        self._click_mode_group.addButton(self._radio_source, self._CLICK_SOURCE)

        click_mode_layout.addWidget(self._radio_target)
        click_mode_layout.addWidget(self._radio_source)
        click_mode_layout.addStretch()

        # Indicator label showing what will happen on click
        self._click_indicator = QLabel("")
        self._click_indicator.setStyleSheet("color: #6c7086; font-size: 11px;")
        click_mode_layout.addWidget(self._click_indicator)

        left_layout.addWidget(click_mode_frame)

        # Field table with category grouping
        self._field_table = QTableWidget()
        self._field_table.setColumnCount(6)
        self._field_table.setHorizontalHeaderLabels(
            ["\ub9e8\ub2e8", "Field", "Min", "Max", "Mean", "Std"]
        )
        self._field_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._field_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        for col in range(2, 6):
            self._field_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )
        self._field_table.verticalHeader().setVisible(False)
        self._field_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._field_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._field_table.setSelectionMode(QTableWidget.SingleSelection)
        self._field_table.cellClicked.connect(self._on_field_clicked)
        left_layout.addWidget(self._field_table, stretch=1)

        # No-data placeholder
        self._no_data_label = QLabel(
            "\ud30c\uc77c\uc744 \ub85c\ub4dc\ud558\uba74 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
        )
        self._no_data_label.setObjectName("subtitleLabel")
        self._no_data_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self._no_data_label)

        main_splitter.addWidget(left_widget)

        # --- Right side: vertical splitter [B] + [C] ---
        right_splitter = QSplitter(Qt.Vertical)

        # --- [B] Edit Builder (right-top) ---
        builder_widget = QWidget()
        builder_layout = QVBoxLayout(builder_widget)
        builder_layout.setContentsMargins(8, 8, 8, 8)
        builder_layout.setSpacing(8)

        builder_title = QLabel("Edit Builder")
        builder_title.setObjectName("sectionLabel")
        builder_layout.addWidget(builder_title)

        builder_card = QFrame()
        builder_card.setObjectName("card")
        card_layout = QVBoxLayout(builder_card)
        card_layout.setSpacing(6)

        # Mode selection
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._mode_combo = QComboBox()
        for key, label, desc in _MODES:
            self._mode_combo.addItem(f"{label} - {desc}", key)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_combo, stretch=1)
        card_layout.addLayout(mode_row)

        # Target field selection
        field_row = QHBoxLayout()
        field_row.addWidget(QLabel("Target Field:"))
        self._field_combo = QComboBox()
        self._field_combo.setEditable(True)
        for name in self._field_names:
            offset = TRACE_FIELD_MAP[name][2]
            self._field_combo.addItem(f"{name}  (byte {offset})", name)
        self._field_combo.currentIndexChanged.connect(self._update_preview)
        field_row.addWidget(self._field_combo, stretch=1)
        card_layout.addLayout(field_row)

        # Dynamic input area
        self._input_grid = QGridLayout()
        self._input_grid.setSpacing(6)
        card_layout.addLayout(self._input_grid)

        # Value input (set mode)
        self._value_label = QLabel("Value:")
        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText(
            "\uc815\uc218 \uac12 \uc785\ub825 (\uc608: -100)"
        )
        self._value_input.textChanged.connect(self._update_preview)
        self._input_grid.addWidget(self._value_label, 0, 0)
        self._input_grid.addWidget(self._value_input, 0, 1)

        # Expression input
        self._expr_label = QLabel("Expression:")
        self._expr_input = QLineEdit()
        self._expr_input.setPlaceholderText(
            "\uc218\uc2dd \uc785\ub825 (\uc608: source_x * 100 + 500000)"
        )
        self._expr_input.textChanged.connect(self._update_preview)
        self._input_grid.addWidget(self._expr_label, 1, 0)
        self._input_grid.addWidget(self._expr_input, 1, 1)

        # Source field (copy mode)
        self._source_label = QLabel("Source Field:")
        self._source_combo = QComboBox()
        self._source_combo.setEditable(True)
        for name in self._field_names:
            self._source_combo.addItem(name, name)
        self._source_combo.currentIndexChanged.connect(self._update_preview)
        self._input_grid.addWidget(self._source_label, 2, 0)
        self._input_grid.addWidget(self._source_combo, 2, 1)

        # CSV file (csv_import mode)
        self._csv_label = QLabel("CSV File:")
        csv_row = QHBoxLayout()
        self._csv_path = QLineEdit()
        self._csv_path.setPlaceholderText("CSV \ud30c\uc77c \uacbd\ub85c")
        csv_row.addWidget(self._csv_path, stretch=1)
        self._csv_browse = QPushButton("\ucc3e\uc544\ubcf4\uae30")
        self._csv_browse.clicked.connect(self._browse_csv)
        csv_row.addWidget(self._csv_browse)
        csv_widget = QWidget()
        csv_widget.setLayout(csv_row)
        self._input_grid.addWidget(self._csv_label, 3, 0)
        self._input_grid.addWidget(csv_widget, 3, 1)

        self._csv_col_label = QLabel("CSV Column:")
        self._csv_col_input = QLineEdit()
        self._csv_col_input.setPlaceholderText(
            "CSV \uc5f4 \uc774\ub984 (\uc608: source_x)"
        )
        self._input_grid.addWidget(self._csv_col_label, 4, 0)
        self._input_grid.addWidget(self._csv_col_input, 4, 1)

        # CSV example info (csv_import mode)
        self._csv_example_label = QLabel(_CSV_EXAMPLE)
        self._csv_example_label.setWordWrap(True)
        self._csv_example_label.setStyleSheet(
            "color: #a6adc8; font-size: 11px; font-family: Consolas, monospace; "
            "background: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 4px; padding: 6px;"
        )
        self._input_grid.addWidget(self._csv_example_label, 5, 0, 1, 2)

        # CSV example file link
        self._csv_create_example = QPushButton(
            "\ud83d\udcc4 \uc608\uc2dc CSV \ud30c\uc77c \uc0dd\uc131"
        )
        self._csv_create_example.setStyleSheet(
            "QPushButton { color: #89b4fa; border: none; text-align: left; "
            "font-size: 11px; padding: 2px; }"
            "QPushButton:hover { color: #b4befe; text-decoration: underline; }"
        )
        self._csv_create_example.clicked.connect(self._create_example_csv)
        self._input_grid.addWidget(self._csv_create_example, 6, 0, 1, 2)

        # Condition (optional)
        cond_row = QHBoxLayout()
        cond_row.addWidget(QLabel("Condition:"))
        self._condition_input = QLineEdit()
        self._condition_input.setPlaceholderText(
            "\uc870\uac74\uc2dd (\uc608: trace_sequence_line > 100)"
        )
        cond_row.addWidget(self._condition_input, stretch=1)
        card_layout.addLayout(cond_row)

        # --- Sample Preview ---
        preview_frame = QFrame()
        preview_frame.setObjectName("card")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(10, 8, 10, 8)

        preview_header = QLabel("Sample Preview")
        preview_header.setObjectName("subtitleLabel")
        preview_header.setStyleSheet("color: #89b4fa; font-weight: bold;")
        preview_layout.addWidget(preview_header)

        self._preview_label = QLabel(
            "Target \ud544\ub4dc\ub97c \uc120\ud0dd\ud558\uba74 \ud604\uc7ac \uac12 \ubc94\uc704\uc640 "
            "\uc218\uc815 \uacb0\uacfc \uc608\uce21\uc774 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
        )
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        preview_layout.addWidget(self._preview_label)

        card_layout.addWidget(preview_frame)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_validate = QPushButton("\uc218\uc2dd \uac80\uc99d")
        self._btn_validate.clicked.connect(self._validate_edit)
        btn_row.addWidget(self._btn_validate)

        self._btn_add = QPushButton("\uc791\uc5c5 \ud050\uc5d0 \ucd94\uac00")
        self._btn_add.setObjectName("primaryButton")
        self._btn_add.clicked.connect(self._add_to_queue)
        btn_row.addWidget(self._btn_add)
        card_layout.addLayout(btn_row)

        # Validation message
        self._msg_label = QLabel("")
        self._msg_label.setWordWrap(True)
        card_layout.addWidget(self._msg_label)

        builder_layout.addWidget(builder_card)
        right_splitter.addWidget(builder_widget)

        # --- [C] Edit Queue (right-bottom) ---
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(8, 8, 8, 8)
        queue_layout.setSpacing(8)

        queue_title = QLabel("Edit Queue")
        queue_title.setObjectName("sectionLabel")
        queue_layout.addWidget(queue_title)

        queue_row = QHBoxLayout()
        self._queue_list = QListWidget()
        queue_row.addWidget(self._queue_list, stretch=1)

        queue_btns = QVBoxLayout()
        self._btn_remove = QPushButton("\uc81c\uac70")
        self._btn_remove.clicked.connect(self._remove_from_queue)
        queue_btns.addWidget(self._btn_remove)

        self._btn_clear_queue = QPushButton("\uc804\uccb4 \ucd08\uae30\ud654")
        self._btn_clear_queue.setObjectName("dangerButton")
        self._btn_clear_queue.clicked.connect(self._clear_queue)
        queue_btns.addWidget(self._btn_clear_queue)
        queue_btns.addStretch()
        queue_row.addLayout(queue_btns)

        queue_layout.addLayout(queue_row)
        right_splitter.addWidget(queue_widget)

        # Right splitter ratio: 70% builder, 30% queue
        right_splitter.setStretchFactor(0, 7)
        right_splitter.setStretchFactor(1, 3)

        main_splitter.addWidget(right_splitter)

        # Main splitter ratio: 38% field inspector, 62% editor
        main_splitter.setStretchFactor(0, 38)
        main_splitter.setStretchFactor(1, 62)

        layout.addWidget(main_splitter)

        # Initialize mode visibility and click indicator
        self._on_mode_changed(0)
        self._update_click_indicator()

    # ==================================================================
    # Public API
    # ==================================================================

    def load_from_info(self, info: SegyFileInfo) -> None:
        """Populate the Field Inspector table from file metadata."""
        self._info = info
        self._populate_field_table()
        self._update_preview()

    def get_edits(self) -> list[TraceHeaderEdit]:
        """Return all edits in the queue."""
        return list(self._edit_queue)

    def clear(self) -> None:
        self._edit_queue.clear()
        self._queue_list.clear()
        self._value_input.clear()
        self._expr_input.clear()
        self._csv_path.clear()
        self._csv_col_input.clear()
        self._condition_input.clear()
        self._msg_label.setText("")
        self._preview_label.setText(
            "Target \ud544\ub4dc\ub97c \uc120\ud0dd\ud558\uba74 \ud604\uc7ac \uac12 \ubc94\uc704\uc640 "
            "\uc218\uc815 \uacb0\uacfc \uc608\uce21\uc774 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
        )

    # ==================================================================
    # Field Inspector
    # ==================================================================

    def _populate_field_table(self) -> None:
        """Fill the Field Inspector table with trace_header_summary stats,
        grouped by category with colored category labels."""
        if not self._info or not self._info.trace_header_summary:
            self._field_table.setRowCount(0)
            self._no_data_label.setVisible(True)
            self._field_table.setVisible(False)
            return

        self._no_data_label.setVisible(False)
        self._field_table.setVisible(True)

        summary = self._info.trace_header_summary

        # Sort fields by category then name
        def _sort_key(name: str) -> tuple[str, str]:
            cat = _FIELD_CATEGORIES.get(name, "9_\uae30\ud0c0")
            return (cat, name)

        fields = sorted(summary.keys(), key=_sort_key)
        self._field_table.setRowCount(len(fields))

        # Category colors (Catppuccin Mocha palette)
        cat_colors = {
            "1_\uc2dc\ud000\uc2a4": "#94e2d5",   # Teal
            "2_CDP": "#f9e2af",          # Yellow
            "3_\uc88c\ud45c": "#89b4fa",          # Blue
            "4_\uc9c0\ud45c": "#a6e3a1",          # Green
            "5_3D": "#cba6f7",           # Mauve
            "6_\uc2dc\uac04": "#fab387",          # Peach
            "7_\uc2a4\ud0c0\ud2f1": "#eba0ac",    # Maroon
            "9_\uae30\ud0c0": "#6c7086",          # Overlay0
        }

        prev_cat = ""
        for row, field_name in enumerate(fields):
            stats = summary[field_name]
            cat = _FIELD_CATEGORIES.get(field_name, "9_\uae30\ud0c0")
            cat_label = _CATEGORY_LABELS.get(cat, "\uae30\ud0c0")
            cat_color = cat_colors.get(cat, "#6c7086")

            # Category column: show label only on first row of category
            if cat != prev_cat:
                cat_item = QTableWidgetItem(cat_label)
                cat_item.setForeground(QColor(cat_color))
                prev_cat = cat
            else:
                cat_item = QTableWidgetItem("")
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
            self._field_table.setItem(row, 0, cat_item)

            # Field name
            name_item = QTableWidgetItem(field_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setForeground(QColor(cat_color))
            self._field_table.setItem(row, 1, name_item)

            # Stats columns
            for col, key in enumerate(["min", "max", "mean", "std"], start=2):
                val = stats.get(key, 0)
                if isinstance(val, float) and val == int(val):
                    text = str(int(val))
                elif isinstance(val, float):
                    text = f"{val:.2f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._field_table.setItem(row, col, item)

    def _on_field_clicked(self, row: int, _col: int) -> None:
        """When a field row is clicked, set as Target or Source field
        depending on the current click mode toggle."""
        item = self._field_table.item(row, 1)  # Column 1 = field name
        if not item:
            return
        field_name = item.text()
        if not field_name:
            return

        if self._click_mode == self._CLICK_TARGET:
            self._set_target_field(field_name)
            self._msg_label.setStyleSheet("color: #89b4fa;")
            self._msg_label.setText(
                f"Target Field \uc124\uc815: {field_name}"
            )
        else:
            self._set_source_field(field_name)
            self._msg_label.setStyleSheet("color: #f9e2af;")
            self._msg_label.setText(
                f"Source Field \uc124\uc815: {field_name}"
            )

    def _set_target_field(self, field_name: str) -> None:
        """Set the Target Field combo to the given field name."""
        for i in range(self._field_combo.count()):
            if self._field_combo.itemData(i) == field_name:
                self._field_combo.setCurrentIndex(i)
                break

    def _set_source_field(self, field_name: str) -> None:
        """Set the Source Field combo, auto-switching to Copy mode."""
        # Auto-switch to Copy mode if not already
        mode = self._mode_combo.currentData()
        if mode != "copy":
            for i in range(self._mode_combo.count()):
                if self._mode_combo.itemData(i) == "copy":
                    self._mode_combo.setCurrentIndex(i)
                    break

        # Set source combo
        for i in range(self._source_combo.count()):
            if self._source_combo.itemData(i) == field_name:
                self._source_combo.setCurrentIndex(i)
                break

    def _on_click_mode_toggled(self, checked: bool) -> None:
        """Update click mode when radio buttons change."""
        if self._radio_target.isChecked():
            self._click_mode = self._CLICK_TARGET
        else:
            self._click_mode = self._CLICK_SOURCE
        self._update_click_indicator()

    def _update_click_indicator(self) -> None:
        """Update the indicator text showing current click behavior."""
        if self._click_mode == self._CLICK_TARGET:
            self._click_indicator.setText(
                "\ud074\ub9ad \u2192 Target"
            )
            self._click_indicator.setStyleSheet(
                "color: #89b4fa; font-size: 11px;"
            )
        else:
            self._click_indicator.setText(
                "\ud074\ub9ad \u2192 Source"
            )
            self._click_indicator.setStyleSheet(
                "color: #f9e2af; font-size: 11px;"
            )

    # ==================================================================
    # Sample Preview
    # ==================================================================

    def _update_preview(self) -> None:
        """Update the preview label based on current target field and mode."""
        if not self._info or not self._info.trace_header_summary:
            return

        mode = self._mode_combo.currentData()
        field_data = self._field_combo.currentData()
        field_name = (
            field_data
            if field_data
            else self._field_combo.currentText().split()[0]
        )

        summary = self._info.trace_header_summary
        stats = summary.get(field_name, {})

        if not stats:
            self._preview_label.setText(
                f"{field_name}: \ud1b5\uacc4 \ub370\uc774\ud130 \uc5c6\uc74c "
                "(\ud30c\uc77c\uc5d0\uc11c \uc0d8\ud50c\ub9c1\ub418\uc9c0 \uc54a\uc740 \ud544\ub4dc)"
            )
            self._preview_label.setStyleSheet("color: #f9e2af; font-size: 13px;")
            return

        min_v = stats.get("min", 0)
        max_v = stats.get("max", 0)
        mean_v = stats.get("mean", 0)

        def _fmt(v: float) -> str:
            return str(int(v)) if v == int(v) else f"{v:.2f}"

        current_info = (
            f"{field_name}: "
            f"\ud604\uc7ac({_fmt(min_v)} ~ {_fmt(max_v)}, mean={_fmt(mean_v)})"
        )

        if mode == "set":
            val_text = self._value_input.text().strip()
            if val_text:
                try:
                    val = int(val_text)
                    text = f"{current_info}\n\u2192 \uc0c8 \uac12: {val}"
                except ValueError:
                    text = (
                        f"{current_info}\n"
                        "\u2192 \uc720\ud6a8\ud55c \uc815\uc218\ub97c \uc785\ub825\ud558\uc138\uc694"
                    )
            else:
                text = current_info
            self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")

        elif mode == "expression":
            expr = self._expr_input.text().strip()
            if expr:
                try:
                    # Build variable context with all available field stats
                    vars_min = {f: s.get("min", 0) for f, s in summary.items()}
                    vars_max = {f: s.get("max", 0) for f, s in summary.items()}

                    eval_min = SafeEvaluator(vars_min)
                    eval_max = SafeEvaluator(vars_max)
                    result_min = eval_min.evaluate(expr)
                    result_max = eval_max.evaluate(expr)

                    r_min = min(result_min, result_max)
                    r_max = max(result_min, result_max)
                    text = (
                        f"{current_info}\n"
                        f"\u2192 \uc218\uc2dd: {expr}\n"
                        f"\u2192 \uc608\uce21 \uacb0\uacfc: "
                        f"({_fmt(r_min)} ~ {_fmt(r_max)})"
                    )
                    self._preview_label.setStyleSheet(
                        "color: #a6e3a1; font-size: 13px;"
                    )
                except Exception as e:
                    text = f"{current_info}\n\u2192 \uc218\uc2dd \uc624\ub958: {e}"
                    self._preview_label.setStyleSheet(
                        "color: #f38ba8; font-size: 13px;"
                    )
            else:
                text = current_info
                self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")

        elif mode == "copy":
            source_data = self._source_combo.currentData()
            source_name = (
                source_data if source_data else self._source_combo.currentText()
            )
            src_stats = summary.get(source_name, {})
            if src_stats:
                s_min = _fmt(src_stats.get("min", 0))
                s_max = _fmt(src_stats.get("max", 0))
                text = (
                    f"{current_info}\n"
                    f"\u2190 \ubcf5\uc0ac \uc18c\uc2a4: "
                    f"{source_name}({s_min} ~ {s_max})"
                )
            else:
                text = (
                    f"{current_info}\n"
                    f"\u2190 {source_name}: \ud1b5\uacc4 \ub370\uc774\ud130 \uc5c6\uc74c"
                )
            self._preview_label.setStyleSheet("color: #89b4fa; font-size: 13px;")

        else:  # csv_import
            csv_path = self._csv_path.text().strip()
            csv_col = self._csv_col_input.text().strip()
            if csv_path and csv_col:
                text = (
                    f"{current_info}\n"
                    f"\u2192 CSV: {Path(csv_path).name}\n"
                    f"\u2192 Column: {csv_col}"
                )
            else:
                text = (
                    f"{current_info}\n"
                    "\u2192 CSV \ud30c\uc77c\uacfc \uc5f4 \uc774\ub984\uc744 \uc9c0\uc815\ud558\uc138\uc694"
                )
            self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")

        self._preview_label.setText(text)

    # ==================================================================
    # Slots
    # ==================================================================

    def _on_mode_changed(self, _index: int = 0) -> None:
        mode = self._mode_combo.currentData()

        self._value_label.setVisible(mode == "set")
        self._value_input.setVisible(mode == "set")
        self._expr_label.setVisible(mode == "expression")
        self._expr_input.setVisible(mode == "expression")
        self._source_label.setVisible(mode == "copy")
        self._source_combo.setVisible(mode == "copy")
        self._csv_label.setVisible(mode == "csv_import")
        self._csv_path.setVisible(mode == "csv_import")
        self._csv_browse.setVisible(mode == "csv_import")
        self._csv_col_label.setVisible(mode == "csv_import")
        self._csv_col_input.setVisible(mode == "csv_import")
        self._csv_example_label.setVisible(mode == "csv_import")
        self._csv_create_example.setVisible(mode == "csv_import")

        self._update_preview()

    def _browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "CSV \ud30c\uc77c \uc120\ud0dd", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self._csv_path.setText(path)

    def _create_example_csv(self) -> None:
        """Generate an example CSV file and set it as the CSV path."""
        path, _ = QFileDialog.getSaveFileName(
            self, "\uc608\uc2dc CSV \ud30c\uc77c \uc800\uc7a5", "trace_header_example.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        example_content = (
            "trace_index,source_x,source_y,group_x,group_y,cdp_x,cdp_y,inline,crossline\n"
            "0,500000,6000000,500050,6000025,500025,6000012,100,200\n"
            "1,500100,6000050,500150,6000075,500125,6000062,100,201\n"
            "2,500200,6000100,500250,6000125,500225,6000112,100,202\n"
            "3,500300,6000150,500350,6000175,500325,6000162,101,200\n"
            "4,500400,6000200,500450,6000225,500425,6000212,101,201\n"
            "5,500500,6000250,500550,6000275,500525,6000262,101,202\n"
            "6,500600,6000300,500650,6000325,500625,6000312,102,200\n"
            "7,500700,6000350,500750,6000375,500725,6000362,102,201\n"
            "8,500800,6000400,500850,6000425,500825,6000412,102,202\n"
            "9,500900,6000450,500950,6000475,500925,6000462,103,200\n"
        )
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(example_content)
            self._csv_path.setText(path)
            self._msg_label.setStyleSheet("color: #a6e3a1;")
            self._msg_label.setText(
                f"\uc608\uc2dc CSV \uc0dd\uc131 \uc644\ub8cc: {Path(path).name}"
            )
        except Exception as e:
            self._msg_label.setStyleSheet("color: #f38ba8;")
            self._msg_label.setText(f"CSV \uc0dd\uc131 \uc2e4\ud328: {e}")

    def _validate_edit(self) -> None:
        edit = self._build_edit()
        if edit is None:
            return

        editor = TraceHeaderEditor()
        err = editor.validate_edit(edit)
        if err:
            self._msg_label.setStyleSheet("color: #f38ba8;")
            self._msg_label.setText(f"Validation Error: {err}")
        else:
            self._msg_label.setStyleSheet("color: #a6e3a1;")
            self._msg_label.setText("Validation OK")

    def _add_to_queue(self) -> None:
        edit = self._build_edit()
        if edit is None:
            return

        editor = TraceHeaderEditor()
        err = editor.validate_edit(edit)
        if err:
            self._msg_label.setStyleSheet("color: #f38ba8;")
            self._msg_label.setText(f"Error: {err}")
            return

        self._edit_queue.append(edit)
        desc = self._describe_edit(edit)
        self._queue_list.addItem(desc)
        self._msg_label.setStyleSheet("color: #a6e3a1;")
        self._msg_label.setText(f"Added: {desc}")

    def _remove_from_queue(self) -> None:
        row = self._queue_list.currentRow()
        if 0 <= row < len(self._edit_queue):
            self._edit_queue.pop(row)
            self._queue_list.takeItem(row)

    def _clear_queue(self) -> None:
        self._edit_queue.clear()
        self._queue_list.clear()

    # ==================================================================
    # Helpers
    # ==================================================================

    def _build_edit(self) -> TraceHeaderEdit | None:
        mode = self._mode_combo.currentData()
        field_data = self._field_combo.currentData()
        field_name = (
            field_data
            if field_data
            else self._field_combo.currentText().split()[0]
        )

        if not field_name:
            self._msg_label.setStyleSheet("color: #f38ba8;")
            self._msg_label.setText(
                "Target field\ub97c \uc120\ud0dd\ud558\uc138\uc694"
            )
            return None

        edit = TraceHeaderEdit(
            field_name=field_name,
            mode=mode,
            condition=self._condition_input.text().strip() or "",
        )

        if mode == "set":
            try:
                edit.value = int(self._value_input.text().strip())
            except ValueError:
                self._msg_label.setStyleSheet("color: #f38ba8;")
                self._msg_label.setText(
                    "\uc815\uc218 \uac12\uc744 \uc785\ub825\ud558\uc138\uc694"
                )
                return None

        elif mode == "expression":
            expr = self._expr_input.text().strip()
            if not expr:
                self._msg_label.setStyleSheet("color: #f38ba8;")
                self._msg_label.setText(
                    "\uc218\uc2dd\uc744 \uc785\ub825\ud558\uc138\uc694"
                )
                return None
            edit.expression = expr

        elif mode == "copy":
            source = self._source_combo.currentData()
            if not source:
                source = self._source_combo.currentText()
            edit.source_field = source

        elif mode == "csv_import":
            csv_path = self._csv_path.text().strip()
            if not csv_path:
                self._msg_label.setStyleSheet("color: #f38ba8;")
                self._msg_label.setText(
                    "CSV \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694"
                )
                return None
            edit.csv_path = csv_path
            edit.csv_column = self._csv_col_input.text().strip()

        return edit

    @staticmethod
    def _describe_edit(edit: TraceHeaderEdit) -> str:
        parts = [f"[{edit.mode.upper()}] {edit.field_name}"]
        if edit.mode == "set":
            parts.append(f"= {edit.value}")
        elif edit.mode == "expression":
            parts.append(f"= {edit.expression}")
        elif edit.mode == "copy":
            parts.append(f"\u2190 {edit.source_field}")
        elif edit.mode == "csv_import":
            parts.append(f"\u2190 CSV:{edit.csv_column}")
        if edit.condition:
            parts.append(f"WHERE {edit.condition}")
        return " ".join(parts)
