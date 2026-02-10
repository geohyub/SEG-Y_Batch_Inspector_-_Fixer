"""Field Inspector widget — displays trace header statistics with category grouping."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.models import SegyFileInfo

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

# Category colors (Catppuccin Mocha palette)
_CAT_COLORS = {
    "1_\uc2dc\ud000\uc2a4": "#94e2d5",   # Teal
    "2_CDP": "#f9e2af",          # Yellow
    "3_\uc88c\ud45c": "#89b4fa",          # Blue
    "4_\uc9c0\ud45c": "#a6e3a1",          # Green
    "5_3D": "#cba6f7",           # Mauve
    "6_\uc2dc\uac04": "#fab387",          # Peach
    "7_\uc2a4\ud0c0\ud2f1": "#eba0ac",    # Maroon
    "9_\uae30\ud0c0": "#6c7086",          # Overlay0
}


# Click mode constants
CLICK_TARGET = 0
CLICK_SOURCE = 1


class FieldInspectorWidget(QWidget):
    """Displays trace header field statistics with category grouping.

    Signals
    -------
    field_clicked(str, int)
        Emitted when a field row is clicked.  Arguments are
        ``(field_name, click_mode)`` where click_mode is
        ``CLICK_TARGET`` or ``CLICK_SOURCE``.
    """

    field_clicked = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_mode = CLICK_TARGET
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Field Inspector")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        desc = QLabel(
            "\ud604\uc7ac \ud30c\uc77c\uc758 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uc785\ub2c8\ub2e4.\n"
            "\ud589\uc744 \ud074\ub9ad\ud558\uba74 \uc544\ub798 \uc120\ud0dd\ub41c \ubaa8\ub4dc\uc5d0 \ub530\ub77c "
            "Target \ub610\ub294 Source Field\uac00 \uc790\ub3d9 \uc124\uc815\ub429\ub2c8\ub2e4."
        )
        desc.setObjectName("subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Click mode toggle
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

        grp = QButtonGroup(self)
        grp.addButton(self._radio_target, CLICK_TARGET)
        grp.addButton(self._radio_source, CLICK_SOURCE)

        click_mode_layout.addWidget(self._radio_target)
        click_mode_layout.addWidget(self._radio_source)
        click_mode_layout.addStretch()

        self._click_indicator = QLabel("")
        self._click_indicator.setStyleSheet("color: #6c7086; font-size: 11px;")
        click_mode_layout.addWidget(self._click_indicator)

        layout.addWidget(click_mode_frame)

        # Field table
        self._field_table = QTableWidget()
        self._field_table.setColumnCount(6)
        self._field_table.setHorizontalHeaderLabels(
            ["\ub9e8\ub2e8", "Field", "Min", "Max", "Mean", "Std"]
        )
        self._field_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._field_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 6):
            self._field_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self._field_table.verticalHeader().setVisible(False)
        self._field_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._field_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._field_table.setSelectionMode(QTableWidget.SingleSelection)
        self._field_table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._field_table, stretch=1)

        # No-data placeholder
        self._no_data_label = QLabel(
            "\ud30c\uc77c\uc744 \ub85c\ub4dc\ud558\uba74 \ud2b8\ub808\uc774\uc2a4 \ud5e4\ub354 \ud1b5\uacc4\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
        )
        self._no_data_label.setObjectName("subtitleLabel")
        self._no_data_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._no_data_label)

        self._update_click_indicator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, info: SegyFileInfo) -> None:
        """Fill the table with trace_header_summary stats."""
        if not info or not info.trace_header_summary:
            self._field_table.setRowCount(0)
            self._no_data_label.setVisible(True)
            self._field_table.setVisible(False)
            return

        self._no_data_label.setVisible(False)
        self._field_table.setVisible(True)

        summary = info.trace_header_summary

        def _sort_key(name: str) -> tuple[str, str]:
            cat = _FIELD_CATEGORIES.get(name, "9_\uae30\ud0c0")
            return (cat, name)

        fields = sorted(summary.keys(), key=_sort_key)
        self._field_table.setRowCount(len(fields))

        prev_cat = ""
        for row, field_name in enumerate(fields):
            stats = summary[field_name]
            cat = _FIELD_CATEGORIES.get(field_name, "9_\uae30\ud0c0")
            cat_label = _CATEGORY_LABELS.get(cat, "\uae30\ud0c0")
            cat_color = _CAT_COLORS.get(cat, "#6c7086")

            if cat != prev_cat:
                cat_item = QTableWidgetItem(cat_label)
                cat_item.setForeground(QColor(cat_color))
                prev_cat = cat
            else:
                cat_item = QTableWidgetItem("")
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
            self._field_table.setItem(row, 0, cat_item)

            name_item = QTableWidgetItem(field_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setForeground(QColor(cat_color))
            self._field_table.setItem(row, 1, name_item)

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

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        item = self._field_table.item(row, 1)
        if item and item.text():
            self.field_clicked.emit(item.text(), self._click_mode)

    def _on_click_mode_toggled(self, _checked: bool) -> None:
        self._click_mode = CLICK_TARGET if self._radio_target.isChecked() else CLICK_SOURCE
        self._update_click_indicator()

    def _update_click_indicator(self) -> None:
        if self._click_mode == CLICK_TARGET:
            self._click_indicator.setText("\ud074\ub9ad \u2192 Target")
            self._click_indicator.setStyleSheet("color: #89b4fa; font-size: 11px;")
        else:
            self._click_indicator.setText("\ud074\ub9ad \u2192 Source")
            self._click_indicator.setStyleSheet("color: #f9e2af; font-size: 11px;")
