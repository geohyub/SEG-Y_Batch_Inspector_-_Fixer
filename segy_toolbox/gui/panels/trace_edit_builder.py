"""Edit Builder widget — constructs trace header edits with live preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from segy_toolbox.core.expression import SafeEvaluator
from segy_toolbox.core.trace_editor import TraceHeaderEditor
from segy_toolbox.io.reader import TRACE_FIELD_MAP
from segy_toolbox.models import SegyFileInfo, TraceHeaderEdit


_MODES = [
    ("set", "Set Value", "\uace0\uc815 \uac12 \uc124\uc815"),
    ("expression", "Expression", "\uc218\uc2dd \ubcc0\ud658 (\uc608: source_x * 100)"),
    ("copy", "Copy Field", "\ub2e4\ub978 \ud544\ub4dc \uac12 \ubcf5\uc0ac"),
    ("csv_import", "CSV Import", "CSV\uc5d0\uc11c \uac12 \uac00\uc838\uc624\uae30"),
]

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


class EditBuilderWidget(QWidget):
    """Form for building a single trace header edit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: SegyFileInfo | None = None
        self._field_names = sorted(TRACE_FIELD_MAP.keys())
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Edit Builder")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
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

        # Target field
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

        # Dynamic inputs
        self._input_grid = QGridLayout()
        self._input_grid.setSpacing(6)
        card_layout.addLayout(self._input_grid)

        # Value input (set mode)
        self._value_label = QLabel("Value:")
        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("\uc815\uc218 \uac12 \uc785\ub825 (\uc608: -100)")
        self._value_input.textChanged.connect(self._update_preview)
        self._input_grid.addWidget(self._value_label, 0, 0)
        self._input_grid.addWidget(self._value_input, 0, 1)

        # Expression input
        self._expr_label = QLabel("Expression:")
        self._expr_input = QLineEdit()
        self._expr_input.setPlaceholderText("\uc218\uc2dd \uc785\ub825 (\uc608: source_x * 100 + 500000)")
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

        # CSV file
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
        self._csv_col_input.setPlaceholderText("CSV \uc5f4 \uc774\ub984 (\uc608: source_x)")
        self._input_grid.addWidget(self._csv_col_label, 4, 0)
        self._input_grid.addWidget(self._csv_col_input, 4, 1)

        self._csv_example_label = QLabel(_CSV_EXAMPLE)
        self._csv_example_label.setWordWrap(True)
        self._csv_example_label.setStyleSheet(
            "color: #a6adc8; font-size: 11px; font-family: Consolas, monospace; "
            "background: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 4px; padding: 6px;"
        )
        self._input_grid.addWidget(self._csv_example_label, 5, 0, 1, 2)

        self._csv_create_example = QPushButton("\ud83d\udcc4 \uc608\uc2dc CSV \ud30c\uc77c \uc0dd\uc131")
        self._csv_create_example.setStyleSheet(
            "QPushButton { color: #89b4fa; border: none; text-align: left; "
            "font-size: 11px; padding: 2px; }"
            "QPushButton:hover { color: #b4befe; text-decoration: underline; }"
        )
        self._csv_create_example.clicked.connect(self._create_example_csv)
        self._input_grid.addWidget(self._csv_create_example, 6, 0, 1, 2)

        # Condition
        cond_row = QHBoxLayout()
        cond_row.addWidget(QLabel("Condition:"))
        self._condition_input = QLineEdit()
        self._condition_input.setPlaceholderText("\uc870\uac74\uc2dd (\uc608: trace_sequence_line > 100)")
        cond_row.addWidget(self._condition_input, stretch=1)
        card_layout.addLayout(cond_row)

        # Sample Preview
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
        btn_row.addWidget(self._btn_add)
        card_layout.addLayout(btn_row)

        # Validation message
        self._msg_label = QLabel("")
        self._msg_label.setWordWrap(True)
        card_layout.addWidget(self._msg_label)

        layout.addWidget(card)
        self._on_mode_changed(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def add_button(self) -> QPushButton:
        return self._btn_add

    @property
    def msg_label(self) -> QLabel:
        return self._msg_label

    def set_file_info(self, info: SegyFileInfo) -> None:
        self._info = info
        self._update_preview()

    def set_target_field(self, field_name: str) -> None:
        for i in range(self._field_combo.count()):
            if self._field_combo.itemData(i) == field_name:
                self._field_combo.setCurrentIndex(i)
                break

    def set_source_field(self, field_name: str) -> None:
        mode = self._mode_combo.currentData()
        if mode != "copy":
            for i in range(self._mode_combo.count()):
                if self._mode_combo.itemData(i) == "copy":
                    self._mode_combo.setCurrentIndex(i)
                    break
        for i in range(self._source_combo.count()):
            if self._source_combo.itemData(i) == field_name:
                self._source_combo.setCurrentIndex(i)
                break

    def build_edit(self) -> TraceHeaderEdit | None:
        """Build a TraceHeaderEdit from the current form state, or None on error."""
        mode = self._mode_combo.currentData()
        field_data = self._field_combo.currentData()
        field_name = field_data if field_data else self._field_combo.currentText().split()[0]

        if not field_name:
            self._set_error("Target field\ub97c \uc120\ud0dd\ud558\uc138\uc694")
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
                self._set_error("\uc815\uc218 \uac12\uc744 \uc785\ub825\ud558\uc138\uc694")
                return None
        elif mode == "expression":
            expr = self._expr_input.text().strip()
            if not expr:
                self._set_error("\uc218\uc2dd\uc744 \uc785\ub825\ud558\uc138\uc694")
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
                self._set_error("CSV \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694")
                return None
            edit.csv_path = csv_path
            edit.csv_column = self._csv_col_input.text().strip()

        return edit

    def clear(self) -> None:
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

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

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
            self, "CSV \ud30c\uc77c \uc120\ud0dd", "", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self._csv_path.setText(path)

    def _create_example_csv(self) -> None:
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
        )
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(example_content)
            self._csv_path.setText(path)
            self._msg_label.setStyleSheet("color: #a6e3a1;")
            self._msg_label.setText(f"\uc608\uc2dc CSV \uc0dd\uc131 \uc644\ub8cc: {Path(path).name}")
        except Exception as e:
            self._set_error(f"CSV \uc0dd\uc131 \uc2e4\ud328: {e}")

    def _validate_edit(self) -> None:
        edit = self.build_edit()
        if edit is None:
            return
        editor = TraceHeaderEditor()
        err = editor.validate_edit(edit)
        if err:
            self._set_error(f"Validation Error: {err}")
        else:
            self._msg_label.setStyleSheet("color: #a6e3a1;")
            self._msg_label.setText("Validation OK")

    def _update_preview(self) -> None:
        if not self._info or not self._info.trace_header_summary:
            return

        mode = self._mode_combo.currentData()
        field_data = self._field_combo.currentData()
        field_name = field_data if field_data else self._field_combo.currentText().split()[0]
        summary = self._info.trace_header_summary
        stats = summary.get(field_name, {})

        if not stats:
            self._preview_label.setText(
                f"{field_name}: \ud1b5\uacc4 \ub370\uc774\ud130 \uc5c6\uc74c (\ud30c\uc77c\uc5d0\uc11c \uc0d8\ud50c\ub9c1\ub418\uc9c0 \uc54a\uc740 \ud544\ub4dc)"
            )
            self._preview_label.setStyleSheet("color: #f9e2af; font-size: 13px;")
            return

        min_v, max_v, mean_v = stats.get("min", 0), stats.get("max", 0), stats.get("mean", 0)

        def _fmt(v):
            return str(int(v)) if v == int(v) else f"{v:.2f}"

        current_info = f"{field_name}: \ud604\uc7ac({_fmt(min_v)} ~ {_fmt(max_v)}, mean={_fmt(mean_v)})"

        if mode == "set":
            val_text = self._value_input.text().strip()
            if val_text:
                try:
                    text = f"{current_info}\n\u2192 \uc0c8 \uac12: {int(val_text)}"
                except ValueError:
                    text = f"{current_info}\n\u2192 \uc720\ud6a8\ud55c \uc815\uc218\ub97c \uc785\ub825\ud558\uc138\uc694"
            else:
                text = current_info
            self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        elif mode == "expression":
            expr = self._expr_input.text().strip()
            if expr:
                try:
                    vars_min = {f: s.get("min", 0) for f, s in summary.items()}
                    vars_max = {f: s.get("max", 0) for f, s in summary.items()}
                    r_min = SafeEvaluator(vars_min).evaluate(expr)
                    r_max = SafeEvaluator(vars_max).evaluate(expr)
                    r_min, r_max = min(r_min, r_max), max(r_min, r_max)
                    text = (
                        f"{current_info}\n\u2192 \uc218\uc2dd: {expr}\n"
                        f"\u2192 \uc608\uce21 \uacb0\uacfc: ({_fmt(r_min)} ~ {_fmt(r_max)})"
                    )
                    self._preview_label.setStyleSheet("color: #a6e3a1; font-size: 13px;")
                except Exception as e:
                    text = f"{current_info}\n\u2192 \uc218\uc2dd \uc624\ub958: {e}"
                    self._preview_label.setStyleSheet("color: #f38ba8; font-size: 13px;")
            else:
                text = current_info
                self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        elif mode == "copy":
            source_data = self._source_combo.currentData()
            source_name = source_data if source_data else self._source_combo.currentText()
            src_stats = summary.get(source_name, {})
            if src_stats:
                text = (
                    f"{current_info}\n\u2190 \ubcf5\uc0ac \uc18c\uc2a4: "
                    f"{source_name}({_fmt(src_stats.get('min', 0))} ~ {_fmt(src_stats.get('max', 0))})"
                )
            else:
                text = f"{current_info}\n\u2190 {source_name}: \ud1b5\uacc4 \ub370\uc774\ud130 \uc5c6\uc74c"
            self._preview_label.setStyleSheet("color: #89b4fa; font-size: 13px;")
        else:  # csv_import
            csv_path = self._csv_path.text().strip()
            csv_col = self._csv_col_input.text().strip()
            if csv_path and csv_col:
                text = f"{current_info}\n\u2192 CSV: {Path(csv_path).name}\n\u2192 Column: {csv_col}"
            else:
                text = f"{current_info}\n\u2192 CSV \ud30c\uc77c\uacfc \uc5f4 \uc774\ub984\uc744 \uc9c0\uc815\ud558\uc138\uc694"
            self._preview_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")

        self._preview_label.setText(text)

    def _set_error(self, msg: str) -> None:
        self._msg_label.setStyleSheet("color: #f38ba8;")
        self._msg_label.setText(msg)
