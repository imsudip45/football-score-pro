import copy
import os
import sys
from math import sqrt

from PySide6.QtCore import Property, QObject, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .backend_service import BackendService
from .backend_sync import control_backend_clock

# Configuration dictionary for colors (exact from Play_On_V007.py)
CONFIG = {
    "colors": {
        "background": "#0f0f0f",
        "panel": "#1a1a1a",
        "card": "#252525",
        "border": "#404040",
        "accent": "#2563eb",
        "button_default": "#374151",
        "button_primary": "#2563eb",
        "button_success": "#059669",
        "button_top": "#2e2d2d",
        "button_buttom": "#1f1e1e",
        "button_danger": "#dc2626",
        "text": "#ffffff",
        "text_subheading": "#d1d5db",
        "text_muted": "#9ca3af",
        "text_success": "#10b981",
        "hover": "#3b82f6",
        "shadow": "rgba(0, 0, 0, 0.5)",
    }
}

TIME_EDITOR_STYLE = """
    QLineEdit {
        background-color: #111827;
        color: #F8FAFC;
        border: 1px solid #475569;
        border-radius: 4px;
        padding: 4px 6px;
    }
    QLineEdit:focus {
        border: 1px solid #38bdf8;
        background-color: #1f2937;
    }
"""


class WhiteCheckmarkCheckBox(QCheckBox):
    """Custom QCheckBox with white checkmark when checked"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Hide default indicator and draw custom one
        self.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                padding: 0px;
            }
            QCheckBox::indicator {
                width: 0px;
                height: 0px;
            }
        """)
        self.setFixedSize(18, 18)  # Reduced size to prevent clipping
        self.setCursor(Qt.PointingHandCursor)  # Show it's clickable
        self.setEnabled(True)  # Ensure it's enabled
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def mousePressEvent(self, event):
        """Ensure mouse clicks are properly handled"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only toggle if enabled (row is selected)
            if self.isEnabled():
                # Toggle the checkbox state
                self.setChecked(not self.isChecked())
                event.accept()
                return
            # If disabled, don't accept event so it can propagate to select row
            event.ignore()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Override to draw custom checkbox with white checkmark"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate checkbox rectangle (16x16, centered in 18x18 widget)
        checkbox_size = 16
        x = (self.width() - checkbox_size) // 2
        y = (self.height() - checkbox_size) // 2

        # Draw checkbox background
        if self.isChecked():
            painter.setBrush(QColor("#10B981"))
            painter.setPen(QPen(QColor("#059669"), 1))
        else:
            painter.setBrush(QColor("#1f2937"))
            painter.setPen(QPen(QColor("#B0B4BB"), 1))

        painter.drawRoundedRect(x, y, checkbox_size, checkbox_size, 3, 3)

        # Draw white checkmark if checked
        if self.isChecked():
            painter.setPen(
                QPen(QColor("white"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            )
            # Draw checkmark: two lines forming a check
            # Left part
            painter.drawLine(
                int(x + checkbox_size * 0.25),
                int(y + checkbox_size * 0.5),
                int(x + checkbox_size * 0.4),
                int(y + checkbox_size * 0.7),
            )
            # Right part
            painter.drawLine(
                int(x + checkbox_size * 0.4),
                int(y + checkbox_size * 0.7),
                int(x + checkbox_size * 0.75),
                int(y + checkbox_size * 0.25),
            )


class _PossessionMixin:
    """Mixin to add home/away possession toggle handlers."""

    def toggle_home_possession(self):
        try:
            self.possession_team = "home"
            print("[PlayOn] Possession toggled: HOME")
            # Hook for any stats/label update if implemented
            if hasattr(self, "update_possession_ui"):
                self.update_possession_ui("home")
        except Exception as e:
            print(f"[PlayOn] Error toggling home possession: {e}")

    def toggle_away_possession(self):
        try:
            self.possession_team = "away"
            print("[PlayOn] Possession toggled: AWAY")
            if hasattr(self, "update_possession_ui"):
                self.update_possession_ui("away")
        except Exception as e:
            print(f"[PlayOn] Error toggling away possession: {e}")


class ModernButton(QPushButton):
    """Custom modern button with hover effects (exact from Play_On_V007.py)"""

    def __init__(self, text="", style_type="primary", parent=None, font_size=13):
        super().__init__(text, parent)
        self.style_type = style_type
        self.font_size = font_size
        self.setMinimumHeight(35)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style()

    def apply_style(self):
        styles = {
            "primary": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {CONFIG["colors"]["button_top"]}, stop:1 #1c1c1c);
                    border: 1px solid {CONFIG["colors"]["text_success"]};
                    color: {CONFIG["colors"]["text"]};
                    padding: 2px 2px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: {self.font_size}px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {CONFIG["colors"]["hover"]}, stop:1 #2563eb);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1d4ed8, stop:1 #1e40af);
                }}
            """,
            "success": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {CONFIG["colors"]["button_success"]}, stop:1 #047857);
                    border: 1px solid {CONFIG["colors"]["button_success"]};
                    color: {CONFIG["colors"]["text"]};
                    padding: 2px 2px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: {self.font_size}px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #10b981, stop:1 {CONFIG["colors"]["button_success"]});
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #047857, stop:1 #065f46);
                }}
            """,
            "danger": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {CONFIG["colors"]["button_danger"]}, stop:1 #b91c1c);
                    border: 1px solid {CONFIG["colors"]["button_danger"]};
                    color: {CONFIG["colors"]["text"]};
                    padding: 8px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: {self.font_size}px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ef4444, stop:1 {CONFIG["colors"]["button_danger"]});
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #b91c1c, stop:1 #991b1b);
                }}
            """,
        }
        self.setStyleSheet(styles.get(self.style_type, styles["primary"]))


class ModernLabel(QLabel):
    """Custom modern label with typography styles (exact from Play_On_V007.py)"""

    def __init__(self, text="", label_type="body", parent=None, font_size=13):
        super().__init__(text, parent)
        self.label_type = label_type
        self.font_size = font_size
        self.apply_style()

    def apply_style(self):
        styles = {
            "heading": f"""
                QLabel {{
                    color: {CONFIG["colors"]["text"]};
                    font-size: {self.font_size}px;
                    font-weight: 700;
                    margin: 10px 0;
                    letter-spacing: -0.5px;
                }}
            """,
            "subheading": f"""
                QLabel {{
                    color: {CONFIG["colors"]["text_subheading"]};
                    font-size: {self.font_size}px;
                    font-weight: 600;
                    margin: 6px 0;
                    letter-spacing: -0.25px;
                }}
            """,
            "body": f"""
                QLabel {{
                    color: {CONFIG["colors"]["text"]};
                    font-size: {self.font_size}px;
                    font-weight: 500;
                    letter-spacing: 0.025em;
                }}
            """,
            "success": f"""
                QLabel {{
                    color: {CONFIG["colors"]["text_success"]};
                    font-size: {self.font_size}px;
                    font-weight: 600;
                    letter-spacing: 0.025em;
                }}
            """,
        }
        self.setStyleSheet(styles.get(self.label_type, styles["body"]))


class CustomSpinBox(QWidget):
    """Custom spin box widget (exact from Play_On_V007.py)"""

    valueChanged = Signal(int)

    def __init__(
        self,
        parent=None,
        font=None,
        range_min=0,
        range_max=100,
        width=80,
        height=80,
        buttons_on_right=False,
        show_buttons=True,
        button_width=20,
        button_height=35,
        style_sheet=None,
    ):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.min_value = range_min
        self.max_value = range_max
        self._value = 0
        self.buttons_on_right = buttons_on_right
        self.show_buttons = show_buttons
        self.button_width = button_width
        self.button_height = button_height
        self.font_size = 24 if font else 13

        main_layout = QHBoxLayout(self) if self.buttons_on_right else QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        if self.buttons_on_right and self.show_buttons:
            input_width = width - self.button_width
            input_height = height
        elif self.show_buttons:
            input_width = width
            input_height = height // 2
        else:
            input_width = width
            input_height = height

        self.input_field = QLineEdit(str(self._value), self)
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_field.setFixedSize(input_width, input_height)
        if font:
            self.input_field.setFont(font)
        if style_sheet:
            self.input_field.setStyleSheet(style_sheet)
        else:
            self.input_field.setStyleSheet(f"""
                QLineEdit {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {CONFIG["colors"]["button_default"]}, stop:1 #4b5563);
                    color: {CONFIG["colors"]["text"]};
                    font-weight: 600;
                    font-size: {self.font_size}px;
                    border-radius: 8px;
                    border: 1px solid {CONFIG["colors"]["border"]};
                    padding: 8px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {CONFIG["colors"]["accent"]};
                }}
            """)
        self.input_field.textChanged.connect(self.on_text_changed)
        self.input_field.editingFinished.connect(self.on_editing_finished)

        if self.show_buttons:
            buttons_layout = QVBoxLayout()
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setSpacing(0)

            self.up_button = ModernButton(
                "\u25b2",
                "primary",
                self,
                font_size=14 if self.buttons_on_right else (16 if height >= 80 else 8),
            )
            self.up_button.setFixedSize(self.button_width, self.button_height)
            self.up_button.clicked.connect(self.increment)

            self.down_button = ModernButton(
                "\u25bc",
                "primary",
                self,
                font_size=14 if self.buttons_on_right else (16 if height >= 80 else 8),
            )
            self.down_button.setFixedSize(self.button_width, self.button_height)
            self.down_button.clicked.connect(self.decrement)

            buttons_layout.addWidget(self.up_button)
            buttons_layout.addWidget(self.down_button)

        if self.buttons_on_right and self.show_buttons:
            main_layout.addWidget(self.input_field)
            main_layout.addLayout(buttons_layout)
        elif self.show_buttons:
            main_layout.addWidget(self.input_field)
            main_layout.addLayout(buttons_layout)
        else:
            main_layout.addWidget(self.input_field)

        self.setLayout(main_layout)

    def value(self):
        try:
            return int(self.input_field.text())
        except ValueError:
            return self._value

    def setValue(self, value):
        if self.min_value <= value <= self.max_value:
            self._value = value
            self.input_field.setText(str(value))
            self.valueChanged.emit(value)

    def increment(self):
        new_value = min(self._value + 1, self.max_value)
        self.setValue(new_value)

    def decrement(self):
        new_value = max(self._value - 1, self.min_value)
        self.setValue(new_value)

    def on_text_changed(self, text):
        try:
            value = int(text)
            if self.min_value <= value <= self.max_value:
                self._value = value
                self.valueChanged.emit(value)
            else:
                self.input_field.setText(str(self._value))
        except ValueError:
            if text.strip() == "":
                pass
            else:
                self.input_field.setText(str(self._value))

    def on_editing_finished(self):
        text = self.input_field.text()
        try:
            value = int(text)
            if not (self.min_value <= value <= self.max_value):
                self.input_field.setText(str(self._value))
        except ValueError:
            if text.strip() == "":
                self.setValue(0)
            else:
                self.input_field.setText(str(self._value))


class FontSizeAnimator(QObject):
    """Font size animator for button animations (exact from Play_On_V007.py)"""

    def __init__(self, widget, original_size):
        super().__init__()
        self.widget = widget
        self._font_size = original_size
        self.original_size = original_size

    def getFontSize(self):
        return self._font_size

    def setFontSize(self, size):
        self._font_size = size
        if isinstance(self.widget, (ModernButton, ModernLabel)):
            self.widget.font_size = size
            self.widget.apply_style()
        else:
            font = self.widget.font()
            font.setPointSize(size)
            self.widget.setFont(font)

    fontSize = Property(int, getFontSize, setFontSize)


class ScorerPanel(QWidget):
    """Scorer panel widget based on Play_On.py implementation"""

    def __init__(self, parent, title, x, y, width=587, height=100):
        super().__init__(parent)
        self.setGeometry(x, y, width, height)
        self.title = title
        self.parent_tab = parent
        self.previous_goal_count = 0  # Track previous goal count

        # Ensure styled background and match MATCH STATISTICS panel
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #252525, stop:1 #1a1a1a);
            border: 2px solid #404040;

        """)

        # Title label with deploy button inside its boundary
        self.title_label = QLabel(title, self)
        self.title_label.setGeometry(10, 10, width - 20, 30)  # Full width title bar
        self.title_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #B0B4BB;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)

        # Deploy button inside the title label boundary (left side)
        self.deploy_button = QPushButton("DEPLOY", self.title_label)
        self.deploy_button.setGeometry(520, 4, 75, 22)
        self.deploy_button.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        self.deploy_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }
        """)
        self.deploy_button.clicked.connect(self.deploy_selected_scorers)

        # Scorer table
        self.scorer_table = QTableWidget(self)
        self.scorer_table.setGeometry(10, 50, width - 20, height - 60)
        # Always create with 30 rows so visibility changes work even after external resets
        self.scorer_table.setRowCount(30)
        self.scorer_table.setColumnCount(6)
        self.scorer_table.setHorizontalHeaderLabels(
            ["Time", "Num", "Name", "Export", "Lock", "Reset"]
        )
        self.scorer_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                font-size: 10px;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                gridline-color: #3a4251;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                font-weight: bold;
                border: 1px solid #5a5a5a;
                color: #8b8b8f;
                padding: 4px;
            }
            QTableWidget::item {
                border: 0px solid #5a5a5a;
                border-bottom: 1px solid #272c39;
                border-right: 1px solid #272c39;
                padding: 2px;
            }
        """)
        scorer_header = self.scorer_table.horizontalHeader()
        scorer_header.setSectionResizeMode(QHeaderView.Fixed)
        scorer_header.setStretchLastSection(False)

        self.scorer_table.setColumnWidth(0, 85)  # Time
        self.scorer_table.setColumnWidth(1, 65)  # Num
        self.scorer_table.setColumnWidth(2, 289)  # Name (wider to fill space)
        self.scorer_table.setColumnWidth(3, 70)  # Export
        self.scorer_table.setColumnWidth(4, 50)  # Lock
        self.scorer_table.setColumnWidth(5, 50)  # Reset

        self.scorer_table.verticalHeader().setVisible(False)
        self.scorer_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.scorer_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Set custom delegate for time column to maintain font size during editing
        from PySide6.QtCore import QRegularExpression
        from PySide6.QtGui import QRegularExpressionValidator
        from PySide6.QtWidgets import QStyledItemDelegate

        class TimeColumnDelegate(QStyledItemDelegate):
            def createEditor(self, parent, option, index):
                editor = super().createEditor(parent, option, index)
                if editor:
                    editor.setFont(QFont("Verdana", 12))
                    # Use shared styling for time editors
                    editor.setStyleSheet(TIME_EDITOR_STYLE)
                    # Add validator to only allow numbers and colon (for time format)
                    # Pattern allows: digits and colon, max 6 chars (e.g., "104:56" or "90:00")
                    # This allows up to 5 digits plus colon symbol, no alphabets
                    regex = QRegularExpression(r"^[0-9:]{0,6}$")
                    validator = QRegularExpressionValidator(regex, editor)
                    editor.setValidator(validator)
                    # Also set max length to prevent too long input
                    editor.setMaxLength(6)
                return editor

            def setModelData(self, editor, model, index):
                """Format the input to MM:SS or MMM:SS format when 3, 4, or 5 digits are entered"""
                text = editor.text().strip()

                # Remove any existing colons to get just digits
                digits_only = text.replace(":", "")

                # Format based on number of digits
                if len(digits_only) == 3:
                    # Format as 0X:XX (e.g., "345" -> "03:45")
                    minutes = digits_only[0].zfill(2)
                    seconds = digits_only[1:3].zfill(2)
                    formatted_text = f"{minutes}:{seconds}"
                elif len(digits_only) == 4:
                    # Format as XX:XX (e.g., "2345" -> "23:45")
                    minutes = digits_only[0:2]
                    seconds = digits_only[2:4]
                    formatted_text = f"{minutes}:{seconds}"
                elif len(digits_only) == 5:
                    # Format as XXX:XX (e.g., "10456" -> "104:56")
                    minutes = digits_only[0:3]
                    seconds = digits_only[3:5]
                    formatted_text = f"{minutes}:{seconds}"
                elif ":" in text:
                    # Already has colon, use as is (but ensure proper format)
                    parts = text.split(":")
                    if len(parts) == 2:
                        minutes = parts[0]
                        seconds = parts[1].zfill(2)
                        formatted_text = f"{minutes}:{seconds}"
                    else:
                        formatted_text = text
                else:
                    # Use text as is if it doesn't match patterns
                    formatted_text = text

                # Set the formatted text to the model
                model.setData(index, formatted_text, Qt.ItemDataRole.EditRole)

        time_delegate = TimeColumnDelegate()
        self.scorer_table.setItemDelegateForColumn(0, time_delegate)

        # Set custom header labels to match cards panel styling
        scorer_header_labels = ["Time", "Num", "Name", "Export", "Lock", "Reset"]
        for col, label in enumerate(scorer_header_labels):
            item = QTableWidgetItem(label)
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            item.setForeground(QColor(CONFIG["colors"]["text"]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scorer_table.setHorizontalHeaderItem(col, item)

        # Initialize table
        self._initialize_table()

    def _get_checkbox_from_cell(self, widget):
        try:
            if widget is None:
                return None
            return widget.findChild(QCheckBox)
        except Exception:
            return None

    def _find_row_for_widget(self, widget, column):
        """Locate the scorer table row that owns the given cell widget."""
        try:
            if not widget or not hasattr(self, "scorer_table"):
                return None
            for row in range(self.scorer_table.rowCount()):
                cell_widget = self.scorer_table.cellWidget(row, column)
                if cell_widget is widget:
                    return row
        except Exception as exc:
            print(f"[ScorerPanel] Failed to find widget row: {exc}")
            return None

    def export_rows(self) -> list:
        """Serialize scorer rows that contain player data."""
        rows = []
        try:
            for row in range(self.scorer_table.rowCount()):
                time_item = self.scorer_table.item(row, 0)
                num_item = self.scorer_table.item(row, 1)
                name_btn = self.scorer_table.cellWidget(row, 2)
                if not name_btn:
                    continue
                name_text = name_btn.text()
                num_text = num_item.text().strip() if num_item else ""
                if not num_text and (not name_text or name_text == "Select Player"):
                    continue
                row_data = {
                    "time": time_item.text() if time_item else "00:00",
                    "number": num_text,
                    "name": name_text,
                    "method": name_btn.property("scoring_method"),
                    "exported": bool(
                        self._get_checkbox_from_cell(
                            self.scorer_table.cellWidget(row, 3)
                        )
                        and self._get_checkbox_from_cell(
                            self.scorer_table.cellWidget(row, 3)
                        ).isChecked()
                    ),
                    "locked": bool(
                        self._get_checkbox_from_cell(
                            self.scorer_table.cellWidget(row, 4)
                        )
                        and self._get_checkbox_from_cell(
                            self.scorer_table.cellWidget(row, 4)
                        ).isChecked()
                    ),
                    "visible": not self.scorer_table.isRowHidden(row),
                }
                rows.append(row_data)
        except Exception as exc:
            print(f"Error exporting scorer rows: {exc}")
        return rows

    def load_rows(self, rows: list):
        """Restore scorer rows from serialized data."""
        try:
            self._initialize_table()
            total_rows = self.scorer_table.rowCount()
            for row in range(total_rows):
                self.scorer_table.hideRow(row)
                num_item = self.scorer_table.item(row, 1)
                if num_item:
                    num_item.setText("")
                name_btn = self.scorer_table.cellWidget(row, 2)
                if name_btn:
                    name_btn.setText("Select Player")
                    name_btn.setProperty("scoring_method", None)
                    name_btn.setToolTip("")
                export_cb = self._get_checkbox_from_cell(
                    self.scorer_table.cellWidget(row, 3)
                )
                if export_cb:
                    export_cb.setChecked(False)
                lock_cb = self._get_checkbox_from_cell(
                    self.scorer_table.cellWidget(row, 4)
                )
                if lock_cb:
                    lock_cb.setChecked(False)
                    lock_cb.setEnabled(False)

            for idx, row_data in enumerate(rows or []):
                if idx >= total_rows:
                    break
                time_item = self.scorer_table.item(idx, 0)
                num_item = self.scorer_table.item(idx, 1)
                name_btn = self.scorer_table.cellWidget(idx, 2)
                select_cb = self._get_checkbox_from_cell(
                    self.scorer_table.cellWidget(idx, 3)
                )
                lock_cb = self._get_checkbox_from_cell(
                    self.scorer_table.cellWidget(idx, 4)
                )

                if time_item and "time" in row_data:
                    time_item.setText(row_data.get("time", "00:00"))
                if num_item:
                    num_item.setText(row_data.get("number", ""))
                if name_btn:
                    name_btn.setText(row_data.get("name", "Select Player"))
                    name_btn.setProperty("scoring_method", row_data.get("method"))
                    tooltip = row_data.get("method")
                    name_btn.setToolTip(
                        tooltip.capitalize()
                        if isinstance(tooltip, str) and tooltip
                        else ""
                    )
                if select_cb:
                    select_cb.setChecked(bool(row_data.get("exported")))
                if lock_cb:
                    lock_cb.setEnabled(True)
                    lock_cb.setChecked(bool(row_data.get("locked")))

                self.scorer_table.showRow(idx)
                if row_data.get("visible", True) is False:
                    self.scorer_table.hideRow(idx)

            self.previous_goal_count = len(rows or [])
        except Exception as exc:
            print(f"Error loading scorer rows: {exc}")

    def _initialize_table(self):
        """Initialize the scorer table with proper structure from Play_On.py"""
        team_type = "home" if "HOME" in self.title else "away"
        try:
            # Ensure the table has required rows even if someone cleared it elsewhere
            if self.scorer_table.rowCount() < 30:
                print(
                    f"DEBUG scorer init: growing rows from {self.scorer_table.rowCount()} to 30 for {team_type}"
                )
                self.scorer_table.setRowCount(30)
        except Exception:
            pass

        for row in range(30):  # Initialize all 30 rows
            # Time column - make editable
            time_item = QTableWidgetItem("00:00")
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            time_item.setFont(QFont("Verdana", 12))
            self.scorer_table.setItem(row, 0, time_item)

            # Number column
            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            self.scorer_table.setItem(row, 1, num_item)

            # Name button
            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_default"]};
                    color: {CONFIG["colors"]["text"]};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            name_btn.setProperty("scoring_method", None)
            name_btn.setToolTip("")
            name_btn.clicked.connect(
                lambda checked, r=row: self.show_player_list(r, team_type)
            )
            self.scorer_table.setCellWidget(row, 2, name_btn)

            # Export checkbox (replaces deploy button)
            select_cb = QCheckBox()
            select_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #10B981;
                    border: 1px solid #059669;
                    border-radius: 2px;
                }
            """)
            select_widget = QWidget()
            select_widget.setStyleSheet("border: 0px; background: transparent;")
            select_layout = QHBoxLayout(select_widget)
            select_layout.addWidget(select_cb)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_layout.setContentsMargins(0, 0, 0, 0)
            self.scorer_table.setCellWidget(row, 3, select_widget)

            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            lock_cb.setEnabled(False)  # Disable Lock checkbox by default
            lock_cb.stateChanged.connect(
                lambda state, r=row: self.toggle_row_lock(r, state)
            )
            lock_widget = QWidget()
            lock_widget.setStyleSheet("border: 0px; background: transparent;")
            lock_layout = QHBoxLayout(lock_widget)
            lock_layout.addWidget(lock_cb)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            self.scorer_table.setCellWidget(row, 4, lock_widget)

            # Reset button
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_danger"]};
                    color: white;
                    border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            reset_btn.clicked.connect(
                lambda checked=False, r=row: self.reset_scorer_row(r)
            )
            self.scorer_table.setCellWidget(row, 5, reset_btn)

        # Hide all rows initially
        for row in range(30):
            self.scorer_table.hideRow(row)

    def show_player_list(self, row, team_type):
        """Show player selection dialog with real team data (UI matches old Football app)"""
        try:
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QHeaderView,
                QMessageBox,
                QPushButton,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
            )

            target_row = row

            sender_button = self.sender()
            print(
                f"[ScorerPanel] show_player_list invoked for requested row {target_row}, sender={sender_button}"
            )
            if isinstance(sender_button, QPushButton) and hasattr(self, "scorer_table"):
                try:
                    global_pos = sender_button.mapToGlobal(
                        sender_button.rect().center()
                    )
                    table_pos = self.scorer_table.viewport().mapFromGlobal(global_pos)
                    index = self.scorer_table.indexAt(table_pos)
                except Exception:
                    index = None

                if index and index.isValid():
                    actual_row = index.row()
                    if actual_row != target_row:
                        print(
                            f"[ScorerPanel] Remapping requested row {target_row} to actual row {actual_row} via indexAt lookup"
                        )
                        target_row = actual_row
                else:
                    for r in range(self.scorer_table.rowCount()):
                        cell_widget = self.scorer_table.cellWidget(r, 2)
                        if cell_widget is sender_button or (
                            cell_widget
                            and cell_widget.findChild(QPushButton) is sender_button
                        ):
                            if r != target_row:
                                print(
                                    f"[ScorerPanel] Remapping requested row {target_row} to actual row {r} based on widget scan"
                                )
                                target_row = r
                            break
            parent_match_created = bool(
                self.parent_tab and getattr(self.parent_tab, "match_created", False)
            )
            if not parent_match_created:
                QMessageBox.warning(
                    None,
                    "No Match Created",
                    "Please create a match in the Match Setup tab first before selecting players.",
                )
                return
            # Get team data from parent tab
            team_data = None
            if hasattr(self, "parent_tab") and self.parent_tab:
                if team_type == "home":
                    team_data = getattr(self.parent_tab, "home_team_data", None)
                else:
                    team_data = getattr(self.parent_tab, "away_team_data", None)

            # If no team data, show warning
            if not team_data or not isinstance(team_data, dict):
                from PySide6.QtWidgets import QMessageBox

                team_label = "Home Team" if team_type == "home" else "Away Team"
                QMessageBox.warning(
                    None,
                    "No Players",
                    f"No players loaded for {team_label}. Please create a match first.",
                )
                return

            # Get playing 11 players (dynamic list that updates with substitutions)
            players = team_data.get("playing_11", [])
            if not players:
                # Fallback: check selected flag in players array
                all_players = team_data.get("players", [])
                players = [p for p in all_players if p.get("selected", False)]

            team_label = "Home Team" if team_type == "home" else "Away Team"

            if not players:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    None,
                    "No Players",
                    f"No playing 11 players available for {team_label}. Please ensure 11 players are selected in Match Setup.",
                )
                return

            sent_off_set = set()
            try:
                if hasattr(self.parent_tab, "sent_off_players"):
                    normalized_team = (
                        "home" if str(team_type).lower().startswith("home") else "away"
                    )
                    sent_off_set = self.parent_tab.sent_off_players.get(
                        normalized_team, set()
                    )
            except Exception:
                sent_off_set = set()

            # Show player selection dialog (UI matches old app)
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Select Player for {team_label}")
            dialog.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #28293A, stop:1 #1e1e1e);
                    color: #B0B4BB;
                }
            """)
            dialog.setFixedSize(620, 600)  # Wider to accommodate scoring method columns

            layout = QVBoxLayout(dialog)

            # Maintain checkbox references per row to enforce single selection
            checkbox_groups = {}

            # Create player table (now includes scoring method columns)
            player_table = QTableWidget(dialog)
            player_table.setColumnCount(5)
            player_table.setHorizontalHeaderLabels(
                ["Player Name", "Number", "Foot", "Head", "Penalty"]
            )
            player_table.setStyleSheet("""
                QTableWidget {
                    background: transparent;
                    border: 1px solid #374151;
                    gridline-color: #374151;
                    selection-background-color: #22c55e;
                    selection-color: #000000;
                    font-size: 14px;
                }
                QHeaderView::section {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    color: #10b981;
                    padding: 8px 6px;
                    border: 1px solid #374151;
                    font-weight: 700;
                    font-size: 14px;
                }
                QTableWidget::item {
                    padding: 6px 4px;
                    border-bottom: 1px solid #374151;
                }
                QTableWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white;
                    font-weight: bold;
                }
            """)

            header = player_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.setSectionResizeMode(3, QHeaderView.Fixed)
            header.setSectionResizeMode(4, QHeaderView.Fixed)
            player_table.setColumnWidth(1, 80)
            for idx in (2, 3, 4):
                player_table.setColumnWidth(idx, 70)

            player_table.verticalHeader().setVisible(False)
            player_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            player_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            player_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

            # Store widget and checkbox references for selection highlighting
            checkbox_widgets = {}  # row -> list of widgets for columns 2, 3, 4
            checkbox_controls = {}  # row -> list of checkboxes (foot, head, penalty)

            # Sort by jersey number like old app
            try:

                def get_jersey_num(player):
                    jersey = (
                        player.get("jersey_number") or player.get("jersey_no") or "0"
                    )
                    try:
                        return int(jersey)
                    except (ValueError, TypeError):
                        return 0

                players = sorted(players, key=get_jersey_num)
            except Exception as e:
                print(f"Error sorting players: {str(e)}")
                # If sorting fails, use original order

            player_table.setRowCount(len(players))
            # Set explicit row height to prevent overflow
            row_height = 32  # Enough for checkbox (20px) + padding
            for row in range(len(players)):
                player_table.setRowHeight(row, row_height)

            def handle_checkbox_state(row_idx, current_key, state):
                """Allow only a single scoring method per row and prevent all from being unchecked."""
                group = checkbox_groups.get(row_idx, {})
                if not group:
                    return

                if state == Qt.CheckState.Checked.value:
                    # Uncheck other methods
                    for key, checkbox in group.items():
                        if key != current_key and isinstance(checkbox, QCheckBox):
                            checkbox.blockSignals(True)
                            checkbox.setChecked(False)
                            checkbox.blockSignals(False)
                elif state == Qt.CheckState.Unchecked.value:
                    # Ensure at least one method remains selected
                    any_checked = any(cb.isChecked() for cb in group.values())
                    if not any_checked:
                        current_checkbox = group.get(current_key)
                        if current_checkbox:
                            current_checkbox.blockSignals(True)
                            current_checkbox.setChecked(True)
                            current_checkbox.blockSignals(False)

            for i, player in enumerate(players):
                # Player name
                name_item = QTableWidgetItem(player.get("full_name", "Unknown"))
                name_item.setData(Qt.ItemDataRole.UserRole, player)
                name_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                player_table.setItem(i, 0, name_item)

                # Jersey number (handle both jersey_number and jersey_no)
                jersey_num = (
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                jersey_item = QTableWidgetItem(str(jersey_num))
                jersey_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                player_table.setItem(i, 1, jersey_item)

                if str(jersey_num) in sent_off_set:
                    color = QColor("#ff4d4f")
                    name_item.setForeground(color)
                    jersey_item.setForeground(color)
                    name_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    jersey_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    tooltip = "Red card — player is no longer available."
                    name_item.setToolTip(tooltip)
                    jersey_item.setToolTip(tooltip)

                # Scoring method checkboxes with white checkmark
                foot_cb = WhiteCheckmarkCheckBox()
                head_cb = WhiteCheckmarkCheckBox()
                penalty_cb = WhiteCheckmarkCheckBox()

                checkbox_groups[i] = {
                    "foot": foot_cb,
                    "head": head_cb,
                    "penalty": penalty_cb,
                }
                foot_cb.setChecked(True)

                # Initially disable all checkboxes - they'll be enabled when row is selected
                foot_cb.setEnabled(False)
                head_cb.setEnabled(False)
                penalty_cb.setEnabled(False)

                # Store checkbox references for enabling/disabling
                checkbox_controls[i] = [foot_cb, head_cb, penalty_cb]

                def add_checkbox(cb, column_index):
                    # Create a placeholder item that allows selection (for row highlighting)
                    placeholder = QTableWidgetItem()
                    placeholder.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    placeholder.setText("")  # Empty text
                    player_table.setItem(i, column_index, placeholder)

                    widget = QWidget()
                    widget.setStyleSheet("border: 0px; background: transparent;")
                    # Store row index for selection
                    widget.setProperty("row_index", i)

                    # Add mouse event handler to select row when clicking on widget area
                    def widget_mouse_press(event):
                        if event.button() == Qt.MouseButton.LeftButton:
                            # Select the entire row when clicking on widget area
                            row_idx = widget.property("row_index")
                            if row_idx is not None:
                                player_table.selectRow(row_idx)
                        # Don't accept the event, let it propagate to checkbox if needed
                        QWidget.mousePressEvent(widget, event)

                    widget.mousePressEvent = widget_mouse_press

                    cb_layout = QHBoxLayout(widget)
                    cb_layout.setContentsMargins(0, 0, 0, 0)  # No margins
                    cb_layout.setSpacing(0)
                    # Add stretch before and after to center the checkbox horizontally
                    cb_layout.addStretch()
                    cb_layout.addWidget(cb)
                    cb_layout.addStretch()
                    # Ensure checkbox receives mouse events
                    cb.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                    cb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    player_table.setCellWidget(i, column_index, widget)

                    # Store widget reference for selection highlighting
                    if i not in checkbox_widgets:
                        checkbox_widgets[i] = []
                    checkbox_widgets[i].append(widget)

                add_checkbox(foot_cb, 2)
                add_checkbox(head_cb, 3)
                add_checkbox(penalty_cb, 4)

                for key, checkbox in checkbox_groups[i].items():
                    checkbox.stateChanged.connect(
                        lambda state, row_idx=i, current_key=key: handle_checkbox_state(
                            row_idx, current_key, state
                        )
                    )

                # Store player data for retrieval
                name_item.setData(Qt.ItemDataRole.UserRole, player)

            # Function to update row highlighting based on selection
            def update_row_highlighting():
                selected_rows = set()
                selection_model = player_table.selectionModel()
                if selection_model:
                    for index in selection_model.selectedIndexes():
                        selected_rows.add(index.row())

                # Update all rows
                for row in range(player_table.rowCount()):
                    is_selected = row in selected_rows
                    # Update checkbox column widgets (columns 2, 3, 4)
                    if row in checkbox_widgets:
                        for widget in checkbox_widgets[row]:
                            if is_selected:
                                # Green gradient background matching the table selection
                                widget.setStyleSheet("""
                                    border: 0px;
                                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #22c55e, stop:1 #16a34a);
                                """)
                            else:
                                widget.setStyleSheet(
                                    "border: 0px; background: transparent;"
                                )

                    # Enable/disable checkboxes based on selection
                    if row in checkbox_controls:
                        for checkbox in checkbox_controls[row]:
                            checkbox.setEnabled(is_selected)

            # Connect selection changed signal
            selection_model = player_table.selectionModel()
            if selection_model:
                selection_model.selectionChanged.connect(update_row_highlighting)

            # Also connect to item selection changed for better coverage
            player_table.itemSelectionChanged.connect(update_row_highlighting)

            layout.addWidget(player_table)

            # Buttons (matching official selector dialog)
            button_layout = QHBoxLayout()

            # OK button
            ok_button = QPushButton("OK")
            ok_button.setFont(QFont("Verdana", 14))
            ok_button.setFixedHeight(44)
            ok_button.setMinimumWidth(120)
            ok_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)

            # Cancel button
            cancel_button = QPushButton("Cancel")
            cancel_button.setFont(QFont("Verdana", 14))
            cancel_button.setFixedHeight(44)
            cancel_button.setMinimumWidth(120)
            cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)

            def update_selection():
                """Handle player selection (logic unchanged)"""
                selected_rows = player_table.selectedIndexes()
                if not selected_rows:
                    print("[ScorerDialog] No player selected when OK pressed")
                    QMessageBox.warning(
                        self,
                        "No Player Selected",
                        "Please select a player before confirming.",
                    )
                    return

                selected_row = selected_rows[0].row()
                name_item = player_table.item(selected_row, 0)
                if (
                    name_item
                    and (name_item.flags() & Qt.ItemFlag.ItemIsSelectable) == 0
                ):
                    number_item = player_table.item(selected_row, 1)
                    jersey_value = number_item.text() if number_item else ""
                    message = "This player cannot be selected."
                    if jersey_value in sent_off_set:
                        message = "This player has received a red card and cannot score again."
                    print(f"[ScorerDialog] Row {selected_row} blocked: {message}")
                    QMessageBox.warning(self, "Player Unavailable", message)
                    dialog.reject()
                    return

                player = None
                if name_item:
                    player = name_item.data(Qt.ItemDataRole.UserRole)
                if player is None and 0 <= selected_row < len(players):
                    player = players[selected_row]

                if isinstance(player, dict):
                    selected_method = None
                    row_group = checkbox_groups.get(selected_row, {})
                    if row_group.get("foot") and row_group["foot"].isChecked():
                        selected_method = "foot"
                    elif row_group.get("head") and row_group["head"].isChecked():
                        selected_method = "head"
                    elif row_group.get("penalty") and row_group["penalty"].isChecked():
                        selected_method = "penalty"

                    if not selected_method:
                        print(
                            f"[ScorerDialog] No scoring method selected for row {selected_row}"
                        )
                        QMessageBox.warning(
                            self,
                            "Select Scoring Method",
                            "Please choose Foot, Head, or Penalty to describe how the goal was scored.",
                        )
                        return

                    print(
                        f"[ScorerDialog] Applying player {player.get('full_name') or player.get('name')} ({player.get('jersey_number') or player.get('jersey_no')}) via {selected_method} to table row {target_row}"
                    )
                    self.set_selected_player(target_row, player, selected_method)
                    dialog.accept()
                else:
                    print(f"[ScorerDialog] Missing player data for row {selected_row}")
                    QMessageBox.warning(
                        self,
                        "Player Data Missing",
                        "Could not read details for the selected player.",
                    )
                    dialog.reject()

            ok_button.clicked.connect(update_selection)
            cancel_button.clicked.connect(dialog.reject)
            player_table.doubleClicked.connect(update_selection)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            # Show dialog
            dialog.exec()

        except Exception as e:
            print(f"Error in show_player_list: {e}")
            import traceback

            traceback.print_exc()

    def set_selected_player(self, row, player, scoring_method=None):
        """Set the selected player in the scorer table along with scoring method"""
        try:
            method = (scoring_method or "").strip().lower() or None
            method_label = method.capitalize() if method else None

            def _get_name(p):
                return (
                    p.get("full_name")
                    or p.get("player_fullname")
                    or p.get("name")
                    or p.get("display_name")
                    or "Unknown"
                )

            player_name = _get_name(player)
            display_name = (
                f"{player_name} ({method_label})" if method_label else player_name
            )
            print(f"[ScorerPanel] Setting row {row + 1} -> {display_name}")
            # Update player name button
            name_btn = self.scorer_table.cellWidget(row, 2)
            if name_btn:
                name_btn.setText(display_name)
                name_btn.setProperty("scoring_method", method)
                if method_label:
                    name_btn.setToolTip(f"Goal via {method_label}")
                else:
                    name_btn.setToolTip("")

            # Update jersey number (support both jersey_number and jersey_no keys)
            num_item = self.scorer_table.item(row, 1)
            if num_item:
                jersey_no = (
                    player.get("jersey_number")
                    or player.get("jersey_no")
                    or player.get("number")
                    or ""
                )
                num_item.setText(str(jersey_no))

            # Enable Lock checkbox since Num is now non-blank
            lock_widget = self.scorer_table.cellWidget(row, 4)
            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb:
                    lock_cb.setEnabled(True)

            # Update time
            time_item = self.scorer_table.item(row, 0)
            if (
                time_item
                and hasattr(self, "parent_tab")
                and hasattr(self.parent_tab, "timer_label")
            ):
                current_time = self.parent_tab.timer_label.text()
                time_item.setText(current_time)

            self.update_row_visibility()

        except Exception as e:
            print(f"Error setting selected player: {e}")

    def deploy_selected_scorers(self):
        """Deploy all selected scorer rows"""
        selected_rows = []
        for row in range(self.scorer_table.rowCount()):
            if not self.scorer_table.isRowHidden(row):
                select_widget = self.scorer_table.cellWidget(row, 3)
                if select_widget:
                    select_cb = select_widget.findChild(QCheckBox)
                    if select_cb and select_cb.isChecked():
                        # Get row data
                        time_item = self.scorer_table.item(row, 0)
                        num_item = self.scorer_table.item(row, 1)
                        name_widget = self.scorer_table.cellWidget(row, 2)

                        time = time_item.text() if time_item else "00:00"
                        num = num_item.text() if num_item else ""
                        name = name_widget.text() if name_widget else "Select Player"
                        scoring_method = None
                        if name_widget:
                            scoring_method = name_widget.property("scoring_method")

                        selected_rows.append(
                            {
                                "row": row,
                                "time": time,
                                "num": num,
                                "name": name,
                                "method": scoring_method,
                            }
                        )

        if selected_rows:
            print(
                f"Deploying {len(selected_rows)} selected scorer(s) from {self.title}:"
            )
            for scorer in selected_rows:
                method_label = scorer.get("method")
                method_text = (
                    method_label.capitalize() if method_label else "Unspecified"
                )
                print(
                    f"  - Row {scorer['row'] + 1}: {scorer['time']} | #{scorer['num']} | {scorer['name']} | Method: {method_text}"
                )
        else:
            print(f"No scorers selected for deployment from {self.title}")

    def deploy_scorer(self, row):
        """Handle Deploy button clicks (legacy method - kept for compatibility)"""
        print(f"Deploy button clicked for scorer row {row}")

    def toggle_row_lock(self, row, state):
        """Enable or disable a row based on Lock checkbox state"""
        try:
            is_locked = state == Qt.CheckState.Checked.value

            # Time column (0) - should remain editable when unlocked
            time_item = self.scorer_table.item(row, 0)
            if time_item:
                if is_locked:
                    time_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                else:
                    time_item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsEditable
                    )

            # Number column (1) - not editable
            num_item = self.scorer_table.item(row, 1)
            if num_item:
                if is_locked:
                    num_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                else:
                    num_item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )

            # Widget columns (Name, Export, Reset buttons)
            for col in [2, 3, 5]:
                widget = self.scorer_table.cellWidget(row, col)
                if widget:
                    widget.setEnabled(not is_locked)
        except Exception as e:
            print(f"Error in toggle_row_lock for row {row}: {str(e)}")

    def reset_scorer_row(self, row, reset_time: bool = False):
        """
        Reset a scorer table row to default values.

        Args:
            row (int): Row index to reset.
            reset_time (bool): When True, also reset the time column back to "00:00".
        """
        try:
            # Check if row is locked
            lock_widget = self.scorer_table.cellWidget(row, 4)
            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb and lock_cb.isChecked():
                    QMessageBox.warning(
                        self,
                        "Row Locked",
                        f"Row {row + 1} is locked and cannot be reset.",
                    )
                    return

            # Reset time if requested
            if reset_time:
                time_item = self.scorer_table.item(row, 0)
                if time_item:
                    time_item.setText("00:00")

            # Reset other data
            num_item = self.scorer_table.item(row, 1)
            if num_item:
                num_item.setText("")

            name_btn = self.scorer_table.cellWidget(row, 2)
            if name_btn:
                name_btn.setText("Select Player")
                name_btn.setProperty("scoring_method", None)
                name_btn.setToolTip("")

            select_widget = self.scorer_table.cellWidget(row, 3)
            if select_widget:
                select_cb = select_widget.findChild(QCheckBox)
                if select_cb:
                    select_cb.setChecked(False)

            # Disable Lock checkbox since Num is now blank
            lock_widget = self.scorer_table.cellWidget(row, 4)
            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb:
                    lock_cb.setChecked(False)
                    lock_cb.setEnabled(False)

            # Do NOT hide rows below - keep them visible
            self.scorer_table.showRow(row)
        except Exception as e:
            print(f"Error in reset_scorer_row for row {row}: {str(e)}")

    def update_row_visibility(self):
        """Update visibility of rows based on goal count"""
        try:
            if hasattr(self.parent_tab, "home_goal_label") and hasattr(
                self.parent_tab, "away_goal_label"
            ):
                if "HOME" in self.title:
                    goal_count = int(self.parent_tab.home_goal_label.text())
                else:
                    goal_count = int(self.parent_tab.away_goal_label.text())

                for row in range(self.scorer_table.rowCount()):
                    if row < goal_count:
                        self.scorer_table.showRow(row)
                    else:
                        self.scorer_table.hideRow(row)
        except Exception as e:
            print(f"Error in update_row_visibility: {str(e)}")

    def update_goals(self, goal_count, current_time):
        """Update goals and show appropriate number of rows"""
        try:
            total_rows = self.scorer_table.rowCount()
            # Show/hide rows based on goal count
            for row in range(total_rows):
                if row < goal_count:
                    self.scorer_table.showRow(row)
                else:
                    self.scorer_table.hideRow(row)

            # If goals increased, update time for new goal rows
            if goal_count > self.previous_goal_count:
                # Find and update time for the next empty row
                for row in range(self.previous_goal_count, goal_count):
                    if row < total_rows:
                        time_item = self.scorer_table.item(row, 0)
                        if time_item and time_item.text() == "00:00":
                            time_item.setText(current_time)
            # If goals decreased, reset the now-hidden rows so they appear fresh later
            elif goal_count < self.previous_goal_count:
                for row in range(goal_count, min(self.previous_goal_count, total_rows)):
                    self.reset_scorer_row(row, reset_time=True)
                    self.scorer_table.hideRow(row)

            # Update previous goal count
            self.previous_goal_count = goal_count

        except Exception as e:
            print(f"Error in update_goals: {str(e)}")


class PlayOnTab(QWidget):
    """Exact Play On Tab implementation based on Play_On_V007.py"""

    def __init__(self, backend_service: BackendService, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service

        # Initialize variables from reference
        self.button_animators = {}
        self.time_type = "Current Time"
        self.selected_guest = ""
        self.selected_commentator = ""
        self.selected_host = ""
        self.selected_special_guest = ""
        self.seconds = 0
        self.timer_running = False
        self.extra_time_enabled = False
        self.extra_time_minutes = 0
        self.home_goals = 0
        self.away_goals = 0
        # Keep scoreboard side labels static by default
        self.static_top_team_labels = True

        # Statistics data storage
        self.stats_data = {
            "home_possession_time": 0,
            "away_possession_time": 0,
            "home_goals": 0,
            "away_goals": 0,
            "home_shots": 0,
            "away_shots": 0,
            "home_shots_on_target": 0,
            "away_shots_on_target": 0,
            "home_fouls": 0,
            "away_fouls": 0,
            "home_yellow_cards": 0,
            "away_yellow_cards": 0,
            "home_red_cards": 0,
            "away_red_cards": 0,
            "home_offsides": 0,
            "away_offsides": 0,
            "home_corners": 0,
            "away_corners": 0,
        }
        # Track players who have been sent off (red card) so other tabs can react
        self.sent_off_players = {"home": set(), "away": set()}
        # Track officials who have been sent off (handled by name because no jersey numbers)
        self.sent_off_officials = {"home": set(), "away": set()}
        # Track which players are currently flagged from cards tables (direct red or double yellow)
        self.cards_sent_off_players = {"home": set(), "away": set()}
        # Track card-driven sent-off officials separately so we can detect removals
        self.cards_sent_off_officials = {"home": set(), "away": set()}

        # Possession tracking variables (from Play_On.py)
        self.home_ball_control_time = 0  # Seconds
        self.away_ball_control_time = 0  # Seconds
        self.current_possession = None  # None, "home", or "away"
        self._suppress_possession_highlight_once = (
            True  # Skip highlight during kickoff selection
        )

        # Team data variables for player selection
        self.home_team_data = None
        self.away_team_data = None
        self.home_selected_rows = []
        self.away_selected_rows = []

        # Match creation gate - prevents data loading until match is created
        self.match_created = False
        self.current_match_id = None

        # Timer setup
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.timeout.connect(self.update_possession_times)

        # Initialize UI
        self.init_play_on_tab()

    def init_play_on_tab(self):
        """Initialize the Play On tab UI with exact reference layout"""
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {CONFIG["colors"]["background"]}, stop:1 {CONFIG["colors"]["panel"]});
            }}
        """)

        # Tournament label (positioned above timer)
        self.tournament_label = QLabel("Tournament Name", self)
        self.tournament_label.setFont(QFont("Verdana", 10, QFont.Weight.Normal))
        self.tournament_label.setStyleSheet(f"""
            QLabel {{

                background: transparent;
                border: none;
            }}
        """)
        self.tournament_label.setGeometry(733, 2, 460, 40)  # Positioned above timer
        self.tournament_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Timer label (adjusted for better visibility)
        self.timer_label = ModernLabel("00:00", "heading", self, font_size=80)
        self.timer_label.setGeometry(
            733, 27, 460, 130
        )  # Positioned immediately below tournament label
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 80px;
                font-weight: 700;
                border: 2px solid {CONFIG["colors"]["border"]};
                border-radius: 16px;
                padding: 5px;
                margin: 10px;
            }}
        """)

        # Create all panels exactly like the reference
        self._create_team_panels()
        self._create_goal_panels()
        self._create_control_panel()
        self._create_extra_timer_panel()
        self._create_stats_panel()
        # Reset button moved to toolbar

        # Add scorer panels (positioned above cards panels)
        self.add_scorer_panels()

        # Add cards panels (positioned below scorer panels)
        self.add_cards_panels()

    def _create_team_panels(self):
        """Create home and away team panels exactly like reference"""
        # Home team panel (adjusted for better visibility)
        self.home_team_panel = QWidget(self)
        self.home_team_panel.setObjectName("homeTeamPanel")
        self.home_team_panel.setGeometry(30, 10, 477, 140)
        self.home_team_panel.setStyleSheet(f"""
            #{self.home_team_panel.objectName()} {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.home_team_image = ModernLabel(
            "NO LOGO\nFOUND", "body", self.home_team_panel
        )
        self.home_team_image.setGeometry(10, 10, 130, 120)
        self.home_team_image.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: 2px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)
        self.home_team_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.home_team_label = ModernLabel(
            "Home Team", "subheading", self.home_team_panel, font_size=15
        )
        self.home_team_label.setGeometry(155, 8, 310, 35)
        self.home_team_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_team_label.setStyleSheet(f"""
            QLabel {{
                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        self.full_team_name = ModernLabel(
            "Team Full Name", "body", self.home_team_panel, font_size=13
        )
        self.full_team_name.setGeometry(155, 50, 310, 35)
        self.full_team_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.full_team_name.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 700;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        self.short_team_name = ModernLabel(
            "Short Name", "body", self.home_team_panel, font_size=13
        )
        self.short_team_name.setGeometry(155, 90, 310, 35)
        self.short_team_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.short_team_name.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        # Away team panel (adjusted for better visibility)
        self.away_team_panel = QWidget(self)
        self.away_team_panel.setObjectName("awayTeamPanel")
        self.away_team_panel.setGeometry(1410, 10, 485, 140)
        self.away_team_panel.setStyleSheet(f"""
            #{self.away_team_panel.objectName()} {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.away_team_image = ModernLabel(
            "NO LOGO\nFOUND", "body", self.away_team_panel
        )
        self.away_team_image.setGeometry(335, 10, 140, 120)
        self.away_team_image.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: 2px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)
        self.away_team_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.away_team_label = ModernLabel(
            "Away Team", "subheading", self.away_team_panel, font_size=15
        )
        self.away_team_label.setGeometry(15, 8, 310, 35)
        self.away_team_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.away_team_label.setStyleSheet(f"""
            QLabel {{
                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        self.away_full_team_name = ModernLabel(
            "Team Full Name", "body", self.away_team_panel, font_size=13
        )
        self.away_full_team_name.setGeometry(15, 50, 310, 35)
        self.away_full_team_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.away_full_team_name.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 700;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        self.away_short_team_name = ModernLabel(
            "Short Name", "body", self.away_team_panel, font_size=13
        )
        self.away_short_team_name.setGeometry(15, 90, 310, 35)
        self.away_short_team_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.away_short_team_name.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 6px;
            }}
        """)

        # Apply initial border highlight (none by default)
        self.update_team_panel_borders()

    def load_match_data(self, match_data: dict):
        """Load match data into the UI (required by main window)"""
        try:
            print(f"DEBUG: Loading match data in Play On tab: {match_data}")
            # Check if match has been created - gate to prevent data loading
            if not self.match_created:
                print("DEBUG: Match not created yet, ignoring data load")
                return

            self.current_match_id = match_data.get("match_id") or match_data.get("id")

            home = (match_data or {}).get("home_team") or {}
            away = (match_data or {}).get("away_team") or {}

            # Store team data for player selection functionality
            self.home_team_data = home
            self.away_team_data = away

            # Update team labels for detail fields only; keep top side labels static if configured
            home_name = home.get("full_name") or home.get("short_name") or "Home Team"
            away_name = away.get("full_name") or away.get("short_name") or "Away Team"

            # Get short names for stats panel headers (prefer short_name over full_name)
            home_short_name = home.get("short_name") or home.get("name") or "Home Team"
            away_short_name = away.get("short_name") or away.get("name") or "Away Team"

            # Update top large side labels only if not static
            if not getattr(self, "static_top_team_labels", False):
                if hasattr(self, "home_team_label"):
                    self.home_team_label.setText(home_name)
                    print(f"DEBUG: Updated home_team_label to: {home_name}")
                else:
                    print("DEBUG: home_team_label not found")
                if hasattr(self, "away_team_label"):
                    self.away_team_label.setText(away_name)
                    print(f"DEBUG: Updated away_team_label to: {away_name}")
                else:
                    print("DEBUG: away_team_label not found")
            else:
                print("DEBUG: Labels are static, not updating top team labels")

            # Always update the stats panel Home/Away headers with short team names
            try:
                if hasattr(self, "stats_home_header_label"):
                    self.stats_home_header_label.setText(home_short_name)
                if hasattr(self, "stats_away_header_label"):
                    self.stats_away_header_label.setText(away_short_name)
            except Exception as e:
                print(f"DEBUG: Unable to update stats header labels: {e}")

            # Update scorer panel titles with team short names
            try:
                if hasattr(self, "home_scorer_panel") and hasattr(
                    self.home_scorer_panel, "title_label"
                ):
                    self.home_scorer_panel.title_label.setText(
                        f"{home_short_name} SCORER PANEL"
                    )
                if hasattr(self, "away_scorer_panel") and hasattr(
                    self.away_scorer_panel, "title_label"
                ):
                    self.away_scorer_panel.title_label.setText(
                        f"{away_short_name} SCORER PANEL"
                    )
            except Exception as e:
                print(f"DEBUG: Unable to update scorer panel titles: {e}")

            # Update cards panel titles with team short names
            try:
                if hasattr(self, "home_card_label"):
                    self.home_card_label.setText(f"{home_short_name} CARDS")
                if hasattr(self, "away_card_label"):
                    self.away_card_label.setText(f"{away_short_name} CARDS")
            except Exception as e:
                print(f"DEBUG: Unable to update cards panel titles: {e}")

            # Always update the smaller detail labels
            if hasattr(self, "full_team_name"):
                self.full_team_name.setText(home.get("full_name") or "Team Full Name")
            else:
                print("DEBUG: full_team_name not found")

            if hasattr(self, "short_team_name"):
                self.short_team_name.setText(home.get("short_name") or "Short Name")
            else:
                print("DEBUG: short_team_name not found")

            if hasattr(self, "away_full_team_name"):
                self.away_full_team_name.setText(
                    away.get("full_name") or "Team Full Name"
                )
            else:
                print("DEBUG: away_full_team_name not found")

            if hasattr(self, "away_short_team_name"):
                self.away_short_team_name.setText(
                    away.get("short_name") or "Short Name"
                )
            else:
                print("DEBUG: away_short_team_name not found")

            # Update tournament name if available
            if hasattr(self, "tournament_label"):
                tournament_name = (match_data or {}).get(
                    "tournament_name", "Tournament Name"
                )
                # Also check for tournament data in fixture
                tournament_data = (match_data or {}).get("tournament", {})
                if isinstance(tournament_data, dict):
                    tournament_name = tournament_data.get(
                        "name", tournament_data.get("tournament_name", tournament_name)
                    )
                self.tournament_label.setText(tournament_name)

            # Load team logos if available
            self._load_team_logos(match_data)

            # Load additional fixture data if available
            self._load_additional_fixture_data(match_data)

            print(f"DEBUG: Loaded teams - Home: {home_name}, Away: {away_name}")
            print(f"DEBUG: Home team players: {len(home.get('players', []))}")
            print(f"DEBUG: Away team players: {len(away.get('players', []))}")

        except Exception as e:
            print(f"Error loading match data: {e}")
            import traceback

            traceback.print_exc()

    def _format_seconds(self, seconds: int) -> str:
        try:
            secs = max(int(seconds or 0), 0)
        except Exception:
            secs = 0
        mins, secs = divmod(secs, 60)
        return f"{mins:02d}:{secs:02d}"

    def _is_checkbox_checked(self, widget) -> bool:
        try:
            if not widget:
                return False
            cb = widget.findChild(QCheckBox)
            return bool(cb and cb.isChecked())
        except Exception:
            return False

    def _set_checkbox_checked(self, widget, value: bool):
        try:
            if not widget:
                return
            cb = widget.findChild(QCheckBox)
            if cb:
                cb.setChecked(bool(value))
        except Exception:
            pass

    def _serialize_card_table(self, table) -> list:
        rows = []
        if not table:
            return rows
        try:
            for row in range(table.rowCount()):
                num_item = table.item(row, 1)
                name_widget = table.cellWidget(row, 2)
                if not name_widget:
                    continue
                name_text = name_widget.text()
                num_text = num_item.text().strip() if num_item else ""
                if not num_text and (not name_text or name_text == "Select Player"):
                    continue
                row_data = {
                    "time": table.item(row, 0).text()
                    if table.item(row, 0)
                    else "00:00",
                    "number": num_text,
                    "name": name_text,
                    "yellow": self._is_checkbox_checked(table.cellWidget(row, 3)),
                    "red": self._is_checkbox_checked(table.cellWidget(row, 4)),
                    "exported": self._is_checkbox_checked(table.cellWidget(row, 5)),
                    "locked": self._is_checkbox_checked(table.cellWidget(row, 6)),
                }
                rows.append(row_data)
        except Exception as exc:
            print(f"Error serializing card table: {exc}")
        return rows

    def _load_card_table_state(self, table, rows, team_type: str):
        if not table:
            return
        try:
            table.setRowCount(0)
            for row_data in rows or []:
                row_index = table.rowCount()
                table.setRowCount(row_index + 1)
                self._initialize_single_card_row(table, row_index, team_type)
                time_item = table.item(row_index, 0)
                num_item = table.item(row_index, 1)
                name_btn = table.cellWidget(row_index, 2)
                if time_item:
                    time_item.setText(row_data.get("time", "00:00"))
                if num_item:
                    num_item.setText(row_data.get("number", ""))
                if name_btn:
                    name_btn.setText(row_data.get("name", "Select Player"))
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 3), row_data.get("yellow")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 4), row_data.get("red")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 5), row_data.get("exported")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 6), row_data.get("locked")
                )
                table.showRow(row_index)
        except Exception as exc:
            print(f"Error loading card table state: {exc}")

    def _apply_stats_to_widgets(self):
        if not hasattr(self, "stats_widgets"):
            return
        try:
            for stat_key, widgets in self.stats_widgets.items():
                if stat_key == "possession_time":
                    home_display = self._format_seconds(
                        self.stats_data.get("home_possession_time", 0)
                    )
                    away_display = self._format_seconds(
                        self.stats_data.get("away_possession_time", 0)
                    )
                    if "home_value" in widgets:
                        widgets["home_value"].setText(home_display)
                    if "away_value" in widgets:
                        widgets["away_value"].setText(away_display)
                elif stat_key == "possession":
                    total = max(
                        self.stats_data.get("home_possession_time", 0)
                        + self.stats_data.get("away_possession_time", 0),
                        1,
                    )
                    home_pct = round(
                        (self.stats_data.get("home_possession_time", 0) / total) * 100
                    )
                    away_pct = 100 - home_pct
                    if "home_value" in widgets:
                        widgets["home_value"].setText(str(home_pct))
                    if "away_value" in widgets:
                        widgets["away_value"].setText(str(away_pct))
                else:
                    home_key = f"home_{stat_key}"
                    away_key = f"away_{stat_key}"
                    if "home_value" in widgets:
                        widgets["home_value"].setText(
                            str(self.stats_data.get(home_key, 0))
                        )
                    if "away_value" in widgets:
                        widgets["away_value"].setText(
                            str(self.stats_data.get(away_key, 0))
                        )
        except Exception as exc:
            print(f"Error applying stats to widgets: {exc}")

    def export_state(self) -> dict:
        """Return a serializable snapshot of the Play On tab runtime state."""
        try:
            state = {
                "match_created": bool(getattr(self, "match_created", False)),
                "home_score": self.home_goals,
                "away_score": self.away_goals,
                "timer": {
                    "seconds": int(getattr(self, "seconds", 0)),
                    "running": bool(getattr(self, "timer_running", False)),
                    "display": self.timer_label.text()
                    if hasattr(self, "timer_label")
                    else "00:00",
                },
                "stats": copy.deepcopy(getattr(self, "stats_data", {})),
                "possession": {
                    "home_time": getattr(self, "home_ball_control_time", 0),
                    "away_time": getattr(self, "away_ball_control_time", 0),
                    "current": getattr(self, "current_possession", None),
                },
                "scorers": {
                    "home": self.home_scorer_panel.export_rows()
                    if hasattr(self, "home_scorer_panel")
                    else [],
                    "away": self.away_scorer_panel.export_rows()
                    if hasattr(self, "away_scorer_panel")
                    else [],
                },
                "cards": {
                    "home": self._serialize_card_table(
                        getattr(self, "home_card_table", None)
                    ),
                    "away": self._serialize_card_table(
                        getattr(self, "away_card_table", None)
                    ),
                },
            }
            return state
        except Exception as exc:
            print(f"Error exporting Play On state: {exc}")
            return {}

    def load_state(self, state: dict):
        """Restore the Play On tab from a saved state dictionary."""
        if not state:
            return
        try:
            self.match_created = True

            timer_state = state.get("timer", {})
            self.seconds = int(timer_state.get("seconds", 0))
            self.timer_running = False
            self.update_timer_display()
            if hasattr(self, "btn_start"):
                self.btn_start.setEnabled(True)
            if hasattr(self, "btn_stop"):
                self.btn_stop.setEnabled(False)
            try:
                self._set_timer_controls_enabled(True)
            except Exception:
                pass

            self.home_goals = int(state.get("home_score", self.home_goals))
            self.away_goals = int(state.get("away_score", self.away_goals))
            if hasattr(self, "home_goal_label"):
                self.home_goal_label.setText(str(self.home_goals))
            if hasattr(self, "away_goal_label"):
                self.away_goal_label.setText(str(self.away_goals))

            saved_stats = state.get("stats")
            if isinstance(saved_stats, dict):
                self.stats_data.update(saved_stats)
            self.stats_data["home_goals"] = self.home_goals
            self.stats_data["away_goals"] = self.away_goals
            self._apply_stats_to_widgets()

            possession = state.get("possession", {})
            self.home_ball_control_time = possession.get(
                "home_time", self.home_ball_control_time
            )
            self.away_ball_control_time = possession.get(
                "away_time", self.away_ball_control_time
            )
            self.current_possession = possession.get("current", self.current_possession)
            self.update_possession_times()

            scorer_state = state.get("scorers", {})
            if hasattr(self, "home_scorer_panel"):
                self.home_scorer_panel.load_rows(scorer_state.get("home", []))
            if hasattr(self, "away_scorer_panel"):
                self.away_scorer_panel.load_rows(scorer_state.get("away", []))

            cards_state = state.get("cards", {})
            self._load_card_table_state(
                getattr(self, "home_card_table", None),
                cards_state.get("home", []),
                "home",
            )
            self._load_card_table_state(
                getattr(self, "away_card_table", None),
                cards_state.get("away", []),
                "away",
            )

            self.update_team_panel_borders()
        except Exception as exc:
            print(f"Error loading Play On state: {exc}")

    def enable_match_data_loading(self):
        """Enable match data loading after match is created"""
        self.match_created = True
        print("DEBUG: Match creation gate opened - data loading enabled")

    def _load_team_logos(self, match_data: dict):
        """Load team logos into the image widgets"""
        try:
            import os

            from PySide6.QtGui import QPixmap

            # Get home team logo
            home_team = match_data.get("home_team", {})
            home_logo_path = None

            # Debug: Print available keys in home_team
            print(
                f"DEBUG: Home team keys: {list(home_team.keys()) if isinstance(home_team, dict) else 'Not a dict'}"
            )

            # Try multiple logo path sources
            if "logo" in home_team and home_team["logo"]:
                home_logo_path = home_team["logo"]
            elif "logo_url" in home_team and home_team["logo_url"]:
                home_logo_path = home_team["logo_url"]
            elif "home_team_logo" in match_data and match_data["home_team_logo"]:
                home_logo_path = match_data["home_team_logo"]

            # Get away team logo
            away_team = match_data.get("away_team", {})
            away_logo_path = None

            # Debug: Print available keys in away_team
            print(
                f"DEBUG: Away team keys: {list(away_team.keys()) if isinstance(away_team, dict) else 'Not a dict'}"
            )

            # Try multiple logo path sources
            if "logo" in away_team and away_team["logo"]:
                away_logo_path = away_team["logo"]
            elif "logo_url" in away_team and away_team["logo_url"]:
                away_logo_path = away_team["logo_url"]
            elif "away_team_logo" in match_data and match_data["away_team_logo"]:
                away_logo_path = match_data["away_team_logo"]

            print(f"DEBUG: Home logo path: {home_logo_path}")
            print(f"DEBUG: Away logo path: {away_logo_path}")

            # Helper to resolve a logo path with multiple fallbacks
            def resolve_logo_path(path_str: str) -> str | None:
                try:
                    project_root = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..")
                    )
                    candidates = []
                    if not path_str:
                        return None
                    if os.path.isabs(path_str):
                        candidates.append(path_str)
                    else:
                        # Given string as-is from project root
                        candidates.append(os.path.join(project_root, path_str))
                        # If it uses @ prefix (placeholder), look under resources/images
                        clean_name = (
                            path_str[1:] if path_str.startswith("@") else path_str
                        )
                        candidates.append(
                            os.path.join(
                                project_root, "resources", "images", clean_name
                            )
                        )
                        # Also try with @ left in case caller included it in filename
                        candidates.append(
                            os.path.join(project_root, "resources", "images", path_str)
                        )
                    for p in candidates:
                        if os.path.exists(p):
                            return p
                    return None
                except Exception:
                    return None

            # Load home team logo
            if home_logo_path and hasattr(self, "home_team_image"):
                resolved_home = resolve_logo_path(home_logo_path)
                print(f"DEBUG: Resolved home logo path: {resolved_home}")
                if resolved_home and os.path.exists(resolved_home):
                    pixmap = QPixmap(resolved_home)
                    if not pixmap.isNull():
                        # Clear text before setting pixmap
                        self.home_team_image.clear()
                        # Scale the pixmap to fit the label while maintaining aspect ratio
                        scaled_pixmap = pixmap.scaled(
                            self.home_team_image.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.home_team_image.setPixmap(scaled_pixmap)
                        self.home_team_image.setScaledContents(
                            False
                        )  # Let scaling handle it
                        print(f"DEBUG: Successfully loaded home team logo")
                    else:
                        print(f"DEBUG: Failed to load home team logo pixmap")
                        self.home_team_image.clear()
                        self.home_team_image.setText("NO LOGO\nFOUND")
                else:
                    print(f"DEBUG: Home team logo file not found")
                    self.home_team_image.clear()
                    self.home_team_image.setText("NO LOGO\nFOUND")
            else:
                if hasattr(self, "home_team_image"):
                    self.home_team_image.clear()
                    self.home_team_image.setText("NO LOGO\nFOUND")
                print(f"DEBUG: No home team logo path found")

            # Load away team logo
            if away_logo_path and hasattr(self, "away_team_image"):
                resolved_away = resolve_logo_path(away_logo_path)
                print(f"DEBUG: Resolved away logo path: {resolved_away}")
                if resolved_away and os.path.exists(resolved_away):
                    pixmap = QPixmap(resolved_away)
                    if not pixmap.isNull():
                        # Clear text before setting pixmap
                        self.away_team_image.clear()
                        # Scale the pixmap to fit the label while maintaining aspect ratio
                        scaled_pixmap = pixmap.scaled(
                            self.away_team_image.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.away_team_image.setPixmap(scaled_pixmap)
                        self.away_team_image.setScaledContents(
                            False
                        )  # Let scaling handle it
                        print(f"DEBUG: Successfully loaded away team logo")
                    else:
                        print(f"DEBUG: Failed to load away team logo pixmap")
                        self.away_team_image.clear()
                        self.away_team_image.setText("NO LOGO\nFOUND")
                else:
                    print(f"DEBUG: Away team logo file not found")
                    self.away_team_image.clear()
                    self.away_team_image.setText("NO LOGO\nFOUND")
            else:
                if hasattr(self, "away_team_image"):
                    self.away_team_image.clear()
                    self.away_team_image.setText("NO LOGO\nFOUND")
                print(f"DEBUG: No away team logo path found")

        except Exception as e:
            print(f"Error loading team logos: {e}")
            import traceback

            traceback.print_exc()
            # Set fallback text if loading fails
            if hasattr(self, "home_team_image"):
                self.home_team_image.setText("NO LOGO\nFOUND")
            if hasattr(self, "away_team_image"):
                self.away_team_image.setText("NO LOGO\nFOUND")

    def _load_additional_fixture_data(self, match_data: dict):
        """Load additional fixture data like logos, venue, etc."""
        try:
            if not match_data:
                return

            # Load team logos if available
            home_team_logo = match_data.get("home_team_logo", "")
            away_team_logo = match_data.get("away_team_logo", "")

            if home_team_logo:
                # TODO: Load and display home team logo
                pass

            if away_team_logo:
                # TODO: Load and display away team logo
                pass

            # Load venue information
            venue = match_data.get("venue", "")
            if venue:
                # TODO: Display venue information if UI component exists
                pass

            # Load match date/time
            match_date = match_data.get("date", "")
            match_time = match_data.get("time", "")
            if match_date or match_time:
                # TODO: Display match timing if UI component exists
                pass

            # Load weather data
            weather = match_data.get("weather", {})
            if weather:
                # TODO: Display weather information if UI component exists
                pass

            # Load attendance
            attendance = match_data.get("attendance", "")
            if attendance:
                # TODO: Display attendance if UI component exists
                pass

        except Exception as e:
            print(f"Error loading additional fixture data: {e}")

    def _create_goal_panels(self):
        """Create goal panels exactly like reference"""
        # Home goal panel (adjusted for better visibility)
        home_goal_panel = QWidget(self)
        home_goal_panel.setGeometry(511, 10, 220, 140)
        home_goal_panel.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.home_goal_label = ModernLabel(
            "0", "heading", home_goal_panel, font_size=80
        )
        self.home_goal_label.setGeometry(15, 10, 120, 120)
        self.home_goal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_goal_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["button_danger"]};
                font-size: 80px;
                font-weight: 700;
                border: 2px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.home_goal_up_button = ModernButton(
            "\u25b2", "primary", home_goal_panel, font_size=30
        )
        self.home_goal_up_button.setGeometry(155, 15, 55, 55)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.home_goal_up_button.clicked.connect(self.increment_home_goals_with_scorer)

        self.home_goal_down_button = ModernButton(
            "\u25bc", "primary", home_goal_panel, font_size=30
        )
        self.home_goal_down_button.setGeometry(155, 75, 55, 55)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.home_goal_down_button.clicked.connect(
            self.decrement_home_goals_with_scorer
        )

        # Away goal panel (adjusted for better visibility)
        away_goal_panel = QWidget(self)
        away_goal_panel.setGeometry(1195, 10, 210, 140)
        away_goal_panel.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.away_goal_label = ModernLabel(
            "0", "heading", away_goal_panel, font_size=80
        )
        self.away_goal_label.setGeometry(80, 10, 120, 120)
        self.away_goal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.away_goal_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["button_danger"]};
                font-size: 80px;
                font-weight: 700;
                border: 2px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}#(155, 15, 55, 55)
        """)

        self.away_goal_up_button = ModernButton(
            "\u25b2", "primary", away_goal_panel, font_size=30
        )
        self.away_goal_up_button.setGeometry(15, 15, 55, 55)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.away_goal_up_button.clicked.connect(self.increment_away_goals_with_scorer)

        self.away_goal_down_button = ModernButton(
            "\u25bc", "primary", away_goal_panel, font_size=30
        )
        self.away_goal_down_button.setGeometry(15, 75, 55, 55)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.away_goal_down_button.clicked.connect(
            self.decrement_away_goals_with_scorer
        )

    def _create_control_panel(self):
        """Create control panel exactly like reference"""
        control_panel = QWidget(self)
        control_panel.setGeometry(670, 160, 580, 180)
        control_panel.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 16px;
            }}
        """)

        self.btn_start = ModernButton("START", "success", control_panel, font_size=30)
        self.btn_start.setGeometry(10, 10, 200, 70)
        animator_start = FontSizeAnimator(self.btn_start, 35)
        self.button_animators[self.btn_start] = animator_start
        self.btn_start.clicked.connect(
            lambda: self.animate_button_click(self.btn_start)
        )
        self.btn_start.clicked.connect(self.start_timer)

        self.btn_half1 = ModernButton(
            "1st\nHALF", "primary", control_panel, font_size=13
        )
        self.btn_half1.setGeometry(220, 10, 70, 70)
        self.btn_half1.setToolTip("Set timer to 00:00")
        animator_half1 = FontSizeAnimator(self.btn_half1, 14)
        self.button_animators[self.btn_half1] = animator_half1
        self.btn_half1.clicked.connect(
            lambda: self.animate_button_click(self.btn_half1)
        )
        self.btn_half1.clicked.connect(lambda: self.set_half(0))

        self.btn_half2 = ModernButton(
            "2nd\nHALF", "primary", control_panel, font_size=13
        )
        self.btn_half2.setGeometry(300, 10, 70, 70)
        self.btn_half2.setToolTip("Set timer to 45:00")
        animator_half2 = FontSizeAnimator(self.btn_half2, 14)
        self.button_animators[self.btn_half2] = animator_half2
        self.btn_half2.clicked.connect(
            lambda: self.animate_button_click(self.btn_half2)
        )
        self.btn_half2.clicked.connect(lambda: self.set_half(45))

        self.btn_stop = ModernButton("STOP", "danger", control_panel, font_size=30)
        self.btn_stop.setGeometry(390, 10, 180, 70)
        # Force bold font
        self.btn_stop.setFont(QFont("Verdana", 30, QFont.Weight.Bold))
        animator_stop = FontSizeAnimator(self.btn_stop, 35)
        self.button_animators[self.btn_stop] = animator_stop
        self.btn_stop.clicked.connect(lambda: self.animate_button_click(self.btn_stop))
        self.btn_stop.clicked.connect(self.stop_timer)
        self.btn_stop.setEnabled(False)

        self.btn_update_time = ModernButton(
            "UPDATE\nTIME", "primary", control_panel, font_size=25
        )
        self.btn_update_time.setGeometry(10, 95, 180, 70)
        self.btn_update_time.setToolTip("Update timer with manual time")
        # Force bold font
        self.btn_update_time.setFont(QFont("Verdana", 25, QFont.Weight.Bold))
        animator_update = FontSizeAnimator(self.btn_update_time, 25)
        self.button_animators[self.btn_update_time] = animator_update
        self.btn_update_time.clicked.connect(
            lambda: self.animate_button_click(self.btn_update_time)
        )
        self.btn_update_time.clicked.connect(self.update_time)

        self.min_label = ModernLabel("MIN", "body", control_panel, font_size=20)
        self.min_label.setGeometry(205, 95, 55, 70)
        self.min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.min_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 18px;
                font-weight: 600;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

        self.min_value = CustomSpinBox(
            control_panel,
            font=QFont("Verdana", 30, QFont.Weight.Bold),
            range_min=0,
            range_max=150,
            width=70,
            height=70,
            buttons_on_right=True,
            show_buttons=False,
        )
        self.min_value.setGeometry(275, 95, 60, 70)

        self.min_up_button = ModernButton(
            "\u25b2", "primary", control_panel, font_size=20
        )
        # Place MIN arrows with a small gap to the right of the MIN box
        self.min_up_button.setGeometry(360, 100, 25, 28)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.min_up_button.clicked.connect(lambda: self.min_value.increment())

        self.min_down_button = ModernButton(
            "\u25bc", "primary", control_panel, font_size=20
        )
        self.min_down_button.setGeometry(360, 135, 25, 28)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.min_down_button.clicked.connect(lambda: self.min_value.decrement())

        self.second_value = CustomSpinBox(
            control_panel,
            font=QFont("Verdana", 30, QFont.Weight.Bold),
            range_min=0,
            range_max=59,
            width=70,
            height=70,
            buttons_on_right=True,
            show_buttons=False,
        )
        self.second_value.setGeometry(400, 95, 70, 70)

        self.sec_up_button = ModernButton(
            "\u25b2", "primary", control_panel, font_size=20
        )
        # Move SEC arrows to the right side of the SEC box (not between MIN and SEC) and shift left slightly
        self.sec_up_button.setGeometry(485, 100, 25, 28)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.sec_up_button.clicked.connect(lambda: self.second_value.increment())

        self.sec_down_button = ModernButton(
            "\u25bc", "primary", control_panel, font_size=20
        )
        self.sec_down_button.setGeometry(485, 135, 25, 28)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.sec_down_button.clicked.connect(lambda: self.second_value.decrement())

        self.second_label = ModernLabel("SEC", "body", control_panel, font_size=18)
        # Nudge SEC label slightly left for balance
        self.second_label.setGeometry(520, 95, 50, 70)
        self.second_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.second_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 18px;
                font-weight: 600;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 10px;
            }}
        """)

    def start_timer(self):
        """Start the match timer."""
        if not self.timer_running:
            # Require kickoff to be selected before starting
            try:
                kickoff_team = getattr(self, "current_possession", None)
                if kickoff_team not in ("home", "away"):
                    try:
                        QMessageBox.warning(
                            self,
                            "Kickoff Required",
                            "Please select a kickoff team before starting the timer.",
                        )
                    except Exception:
                        pass
                    return
            except Exception:
                # If property not present, be conservative and block start
                try:
                    QMessageBox.warning(
                        self,
                        "Kickoff Required",
                        "Please select a kickoff team before starting the timer.",
                    )
                except Exception:
                    pass
                return
            self.timer.start(1000)
            self.timer_running = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            # Disable time-setting controls while running
            self._set_timer_controls_enabled(False)
            if getattr(self, "current_match_id", None):
                control_backend_clock(
                    self.current_match_id, "start", getattr(self, "seconds", 0)
                )

    def stop_timer(self):
        """Stop the match timer."""
        self.timer.stop()
        self.timer_running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # Re-enable time-setting controls when stopped
        self._set_timer_controls_enabled(True)
        if getattr(self, "current_match_id", None):
            control_backend_clock(
                self.current_match_id, "stop", getattr(self, "seconds", 0)
            )

    def set_half(self, minutes):
        """Set the timer to a specific half duration."""
        self.seconds = minutes * 60
        self.update_timer_display()

    def update_time(self):
        """Update the timer based on manual input."""
        min_value = int(self.min_value.value())
        sec_value = int(self.second_value.value())
        self.seconds = (min_value * 60) + sec_value
        self.update_timer_display()

    def update_timer(self):
        """Increment the timer and update the display."""
        self.seconds += 1
        self.update_timer_display()

    def update_timer_display(self):
        """Update the timer label display."""
        mins, secs = divmod(self.seconds, 60)
        display_text = f"{mins:02d}:{secs:02d}"
        self.timer_label.setText(display_text)

    # --- Possession time editing helpers ---
    def _configure_possession_line_edit(self, line_edit, team: str):
        """Set up possession time fields to allow editing only via context menu."""
        try:
            line_edit.setReadOnly(True)
            line_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            line_edit.customContextMenuRequested.connect(
                lambda pos, w=line_edit, t=team: self._show_possession_context_menu(
                    w, pos, t
                )
            )
            line_edit.editingFinished.connect(
                lambda w=line_edit, t=team: self._on_possession_line_edit_finished(w, t)
            )
        except Exception:
            pass

    def _show_possession_context_menu(self, line_edit, pos, team: str):
        """Display context menu to unlock possession time editing."""
        try:
            menu = QMenu(line_edit)
            edit_action = menu.addAction("Edit Possession Time")
            chosen = menu.exec(line_edit.mapToGlobal(pos))
            if chosen == edit_action:
                line_edit.setReadOnly(False)
                line_edit.setFocus()
                line_edit.selectAll()
        except Exception:
            pass

    def _on_possession_line_edit_finished(self, line_edit, team: str):
        """Handle editing completion: lock field and persist changes."""
        try:
            line_edit.setReadOnly(True)
        except Exception:
            pass
        self._on_possession_time_edit(team, line_edit.text())

    def _on_possession_time_edit(self, team: str, text: str):
        """Parse edited mm:ss for possession and update internal seconds and labels.
        team: 'home' or 'away'
        text: mm:ss string
        """
        try:
            seconds = self._parse_mmss_to_seconds(text)
            total_elapsed = max(int(getattr(self, "seconds", 0)), 0)
            total_elapsed = max(total_elapsed, 1)  # avoid division by zero
            seconds = min(seconds, total_elapsed)
            if team == "home":
                self.home_ball_control_time = seconds
                # Remaining time goes to away team
                self.away_ball_control_time = max(0, total_elapsed - seconds)
            else:
                self.away_ball_control_time = seconds
                # Remaining time goes to home team
                self.home_ball_control_time = max(0, total_elapsed - seconds)
            self._rebalance_possession_times()
            # Also reflect formatted text back to the field to normalize
            display = self._format_seconds_to_mmss(seconds)
            if "possession_time" in getattr(self, "stats_widgets", {}):
                key = "home_value" if team == "home" else "away_value"
                try:
                    self.stats_widgets["possession_time"][key].setText(display)
                except Exception:
                    pass
            # Optionally update possession percentages/time displays if applicable
            try:
                self.update_possession_times()
            except Exception:
                pass
        except Exception:
            try:
                QMessageBox.warning(
                    self, "Invalid Time", "Please enter possession time as mm:ss"
                )
            except Exception:
                pass

    def _parse_mmss_to_seconds(self, mmss: str) -> int:
        parts = str(mmss).split(":")
        if len(parts) != 2:
            raise ValueError("bad time")
        m = int(parts[0]) if parts[0].isdigit() else 0
        s = int(parts[1]) if parts[1].isdigit() else 0
        if s >= 60:
            s = 59
        if m < 0:
            m = 0
        return m * 60 + s

    def _format_seconds_to_mmss(self, seconds: int) -> str:
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _set_timer_controls_enabled(self, enabled: bool):
        """Enable/disable controls that adjust timer or halves while clock runs."""
        # Half buttons
        if hasattr(self, "btn_half1"):
            self.btn_half1.setEnabled(enabled)
        if hasattr(self, "btn_half2"):
            self.btn_half2.setEnabled(enabled)
        # Update time button and inputs
        if hasattr(self, "btn_update_time"):
            self.btn_update_time.setEnabled(enabled)
        for attr in [
            "min_value",
            "second_value",
            "min_up_button",
            "min_down_button",
            "sec_up_button",
            "sec_down_button",
        ]:
            if hasattr(self, attr):
                try:
                    getattr(self, attr).setEnabled(enabled)
                except Exception:
                    pass
        # Optional reset buttons if present in UI (guarded)
        for attr in ["reset_match_button", "reset_timer_button"]:
            if hasattr(self, attr):
                try:
                    getattr(self, attr).setEnabled(enabled)
                except Exception:
                    pass

    def get_current_time_text(self):
        """Return the current match time as mm:ss from the running counter."""
        try:
            total_seconds = int(getattr(self, "seconds", 0))
            mins, secs = divmod(total_seconds, 60)
            formatted = f"{mins:02d}:{secs:02d}"
            return formatted
        except Exception:
            return "00:00"

    def increment_home_goals_with_scorer(self):
        """Increment home team goals and update scorer panel"""
        self.home_goals += 1
        self.stats_data["home_goals"] = self.home_goals
        self.home_goal_label.setText(str(self.home_goals))
        # Ensure shots on target >= goals (and increments shots via existing linkage)
        self.increase_stat("shots_on_target", "home")
        # Enforce invariants after goal changes
        self._enforce_stats_invariants("home")

        # Update scorer panel if it exists
        if hasattr(self, "home_scorer_panel"):
            self._ensure_scorer_panel_initialized("home")
            current_time = self.timer_label.text()
            self.home_scorer_panel.update_goals(self.home_goals, current_time)
            self._debug_dump_scorer_rows("home")
            # Fallback: force visibility to match goal count
            try:
                for r in range(self.home_scorer_panel.scorer_table.rowCount()):
                    self.home_scorer_panel.scorer_table.setRowHidden(
                        r, r >= self.home_goals
                    )
            except Exception:
                pass

        # Update stats widgets
        if hasattr(self, "stats_widgets") and "goals" in self.stats_widgets:
            self.stats_widgets["goals"]["home_value"].setText(str(self.home_goals))

    def decrement_home_goals_with_scorer(self):
        """Decrement home team goals and update scorer panel"""
        try:
            print(f"DEBUG home before-- goals={self.home_goals}")
        except Exception:
            pass
        if self.home_goals > 0:
            self.home_goals -= 1
            self.stats_data["home_goals"] = self.home_goals
        self.home_goal_label.setText(str(self.home_goals))
        try:
            print(
                f"DEBUG goals: home decrement -> goals={self.home_goals}, SOT={self.stats_data.get('home_shots_on_target', 0)}, shots={self.stats_data.get('home_shots', 0)}"
            )
        except Exception:
            pass

        # Update scorer panel if it exists
        if hasattr(self, "home_scorer_panel"):
            self._ensure_scorer_panel_initialized("home")
            current_time = self.timer_label.text()
            self.home_scorer_panel.update_goals(self.home_goals, current_time)
            self._debug_dump_scorer_rows("home")
            # Fallback: force visibility to match goal count
            try:
                for r in range(self.home_scorer_panel.scorer_table.rowCount()):
                    self.home_scorer_panel.scorer_table.setRowHidden(
                        r, r >= self.home_goals
                    )
            except Exception:
                pass

        # Update stats widgets
        if hasattr(self, "stats_widgets") and "goals" in self.stats_widgets:
            self.stats_widgets["goals"]["home_value"].setText(str(self.home_goals))
        # Enforce invariants after goal changes
        self._enforce_stats_invariants("home")
        # Reduce shots on target by 1 only if above new goals
        if self.stats_data.get("home_shots_on_target", 0) > self.home_goals:
            self.decrease_stat("shots_on_target", "home")

    def increment_away_goals_with_scorer(self):
        """Increment away team goals and update scorer panel"""
        try:
            print(f"DEBUG away before++ goals={self.away_goals}")
        except Exception:
            pass
        self.away_goals += 1
        self.stats_data["away_goals"] = self.away_goals
        self.away_goal_label.setText(str(self.away_goals))
        try:
            print(
                f"DEBUG goals: away increment -> goals={self.away_goals}, SOT={self.stats_data.get('away_shots_on_target', 0)}, shots={self.stats_data.get('away_shots', 0)}"
            )
        except Exception:
            pass
        # Ensure shots on target >= goals (and increments shots via existing linkage)
        self.increase_stat("shots_on_target", "away")
        # Enforce invariants after goal changes
        self._enforce_stats_invariants("away")

        # Update scorer panel if it exists
        if hasattr(self, "away_scorer_panel"):
            self._ensure_scorer_panel_initialized("away")
            current_time = self.timer_label.text()
            self.away_scorer_panel.update_goals(self.away_goals, current_time)
            self._debug_dump_scorer_rows("away")
            # Fallback: force visibility to match goal count
            try:
                for r in range(self.away_scorer_panel.scorer_table.rowCount()):
                    self.away_scorer_panel.scorer_table.setRowHidden(
                        r, r >= self.away_goals
                    )
            except Exception:
                pass

        # Update stats widgets
        if hasattr(self, "stats_widgets") and "goals" in self.stats_widgets:
            self.stats_widgets["goals"]["away_value"].setText(str(self.away_goals))

    def decrement_away_goals_with_scorer(self):
        """Decrement away team goals and update scorer panel"""
        try:
            print(f"DEBUG away before-- goals={self.away_goals}")
        except Exception:
            pass
        if self.away_goals > 0:
            self.away_goals -= 1
            self.stats_data["away_goals"] = self.away_goals
        self.away_goal_label.setText(str(self.away_goals))
        try:
            print(
                f"DEBUG goals: away decrement -> goals={self.away_goals}, SOT={self.stats_data.get('away_shots_on_target', 0)}, shots={self.stats_data.get('away_shots', 0)}"
            )
        except Exception:
            pass

        # Update scorer panel if it exists
        if hasattr(self, "away_scorer_panel"):
            self._ensure_scorer_panel_initialized("away")
            current_time = self.timer_label.text()
            self.away_scorer_panel.update_goals(self.away_goals, current_time)
            self._debug_dump_scorer_rows("away")
            # Fallback: force visibility to match goal count
            try:
                for r in range(self.away_scorer_panel.scorer_table.rowCount()):
                    self.away_scorer_panel.scorer_table.setRowHidden(
                        r, r >= self.away_goals
                    )
            except Exception:
                pass

        # Update stats widgets
        if hasattr(self, "stats_widgets") and "goals" in self.stats_widgets:
            self.stats_widgets["goals"]["away_value"].setText(str(self.away_goals))
        # Enforce invariants after goal changes
        self._enforce_stats_invariants("away")
        # Reduce shots on target by 1 only if above new goals
        if self.stats_data.get("away_shots_on_target", 0) > self.away_goals:
            self.decrease_stat("shots_on_target", "away")

    def add_scorer_panels(self):
        """Add scorer panels to the main interface (positioned above cards panels)"""
        # Home Scorer Panel (positioned above home cards panel)
        self.home_scorer_panel = ScorerPanel(
            self,
            "HOME SCORER PANEL",
            30,
            160,  # Positioned above cards
            635,
            350,  # Increased height to better utilize space
        )

        # Away Scorer Panel (positioned above away cards panel)
        self.away_scorer_panel = ScorerPanel(
            self,
            "AWAY SCORER PANEL",
            1260,
            160,  # Positioned above cards
            635,
            350,  # Increased height to better utilize space
        )

    def add_cards_panels(self):
        """Add cards panels below the scorer panels"""
        # Home Cards Panel (using Substituted.py implementation)
        home_card_panel = QWidget(self)
        home_card_panel.setGeometry(
            30, 520, 634, 430
        )  # Positioned below taller scorer panel (360+180+10=550)
        home_card_panel.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252525, stop:1 #1a1a1a);
                border: 2px solid #404040;
            }
        """)

        # Home Card Label - store reference for dynamic updates
        self.home_card_label = QLabel("HOME CARDS", home_card_panel)
        self.home_card_label.setGeometry(10, 10, 612, 30)
        self.home_card_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.home_card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_card_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #B0B4BB;
                border: 1px solid #404040;
            }
        """)

        # Home Card Table
        self.home_card_table = QTableWidget(home_card_panel)
        self.home_card_table.setGeometry(10, 50, 612, 368)
        self.home_card_table.setRowCount(0)
        self.home_card_table.setColumnCount(
            8
        )  # Time, Num, Name, Yellow, Red, Select, Lock, Reset
        self.home_card_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                font-size: 10px;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                gridline-color: #3a4251;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                font-weight: bold;
                color: #8b8b8f;
                border: 1px solid #5a5a5a;
                padding: 4px;
            }
            QTableWidget::item {
                border: 0px solid #5a5a5a;
                border-bottom: 1px solid #272c39;
                border-right: 1px solid #272c39;
                padding: 2px;
            }
            QTableWidget::item:3 {
                color:yellow;
                }
            QTableWidget::item:4 {
                color:red;
                }
        """)
        # Optimize column widths
        self.home_card_table.setColumnWidth(0, 85)  # Time
        self.home_card_table.setColumnWidth(1, 58)  # Num
        self.home_card_table.setColumnWidth(2, 234)  # Name
        self.home_card_table.setColumnWidth(3, 60)  # Yellow
        self.home_card_table.setColumnWidth(4, 40)  # Red
        self.home_card_table.setColumnWidth(5, 49)  # Export
        self.home_card_table.setColumnWidth(6, 40)  # Lock
        self.home_card_table.setColumnWidth(7, 40)  # Reset
        self.home_card_table.verticalHeader().setVisible(False)
        self.home_card_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )

        # Set custom header labels for Home Card Table (with Select)
        card_header_labels = [
            "Time",
            "Num",
            "Name",
            "Yellow",
            "Red",
            "Export",
            "Lock",
            "Reset",
        ]
        for col, label in enumerate(card_header_labels):
            item = QTableWidgetItem(label)
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if label == "Yellow":
                item.setForeground(QColor("#FFFF00"))
            elif label == "Red":
                item.setForeground(QColor("#FF0000"))
            else:
                item.setForeground(QColor(CONFIG["colors"]["text"]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.home_card_table.setHorizontalHeaderItem(col, item)
        home_header = self.home_card_table.horizontalHeader()
        home_header.setSectionResizeMode(QHeaderView.Fixed)
        home_header.setStretchLastSection(False)

        # Home Card Table starts empty - rows will be added via + button

        # Add a + button inside Home Cards title label (left side)
        self.home_cards_add_btn = QPushButton("+", self.home_card_label)
        self.home_cards_add_btn.setGeometry(10, 4, 30, 22)
        self.home_cards_add_btn.setFont(QFont("Verdana", 12, QFont.Weight.ExtraBold))
        self.home_cards_add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: white;
                border: 1px solid #2d3748;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6578;
            }
        """)
        self.home_cards_add_btn.clicked.connect(
            lambda: self.add_card_row(self.home_card_table, "home")
        )

        # Add a Deploy button inside Home Cards title label
        self.home_cards_deploy_btn = QPushButton("DEPLOY", self.home_card_label)
        self.home_cards_deploy_btn.setGeometry(530, 4, 75, 22)
        self.home_cards_deploy_btn.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        self.home_cards_deploy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }
        """)
        self.home_cards_deploy_btn.clicked.connect(
            lambda: self.deploy_selected_cards(self.home_card_table, "home")
        )

        # Away Cards Panel (using Substituted.py implementation)
        away_card_panel = QWidget(self)
        away_card_panel.setGeometry(
            1260, 520, 635, 430
        )  # Positioned below taller scorer panel (360+180+10=550)
        away_card_panel.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252525, stop:1 #1a1a1a);
                border: 2px solid #404040;

            }
        """)

        # Away Card Label - store reference for dynamic updates
        self.away_card_label = QLabel("AWAY CARDS", away_card_panel)
        self.away_card_label.setGeometry(10, 10, 612, 30)
        self.away_card_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.away_card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.away_card_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #B0B4BB;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)

        # Add a + button inside Away Cards title label (left side)
        self.away_cards_add_btn = QPushButton("+", self.away_card_label)
        self.away_cards_add_btn.setGeometry(10, 4, 30, 22)
        self.away_cards_add_btn.setFont(QFont("Verdana", 12, QFont.Weight.ExtraBold))
        self.away_cards_add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: white;
                border: 1px solid #2d3748;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6578;
            }
        """)
        self.away_cards_add_btn.clicked.connect(
            lambda: self.add_card_row(self.away_card_table, "away")
        )

        # Add a Deploy button inside Away Cards title label
        self.away_cards_deploy_btn = QPushButton("DEPLOY", self.away_card_label)
        self.away_cards_deploy_btn.setGeometry(530, 4, 75, 22)
        self.away_cards_deploy_btn.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        self.away_cards_deploy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }
        """)
        self.away_cards_deploy_btn.clicked.connect(
            lambda: self.deploy_selected_cards(self.away_card_table, "away")
        )

        # Away Card Table
        self.away_card_table = QTableWidget(away_card_panel)
        self.away_card_table.setGeometry(10, 50, 612, 368)
        self.away_card_table.setRowCount(0)
        self.away_card_table.setColumnCount(
            8
        )  # Time, Num, Name, Yellow, Red, Select, Lock, Reset
        self.away_card_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                font-size: 10px;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                gridline-color: #3a4251;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                font-weight: bold;
                color: #8b8b8f;
                border: 1px solid #5a5a5a;
                padding: 4px;
            }
            QTableWidget::item {
                border: 0px solid #5a5a5a;
                border-bottom: 1px solid #272c39;
                border-right: 1px solid #272c39;
                padding: 2px;
            }
            QTableWidget::item:3 {
                color:yellow;
                }
            QTableWidget::item:4 {
                color:red;
                }
        """)
        # Optimize column widths
        self.away_card_table.setColumnWidth(0, 85)  # Time
        self.away_card_table.setColumnWidth(1, 58)  # Num
        self.away_card_table.setColumnWidth(2, 234)  # Name
        self.away_card_table.setColumnWidth(3, 60)  # Yellow
        self.away_card_table.setColumnWidth(4, 40)  # Red
        self.away_card_table.setColumnWidth(5, 49)  # Export
        self.away_card_table.setColumnWidth(6, 40)  # Lock
        self.away_card_table.setColumnWidth(7, 40)  # Reset
        # Set custom header labels for Away Card Table (reuse same labels)
        for col, label in enumerate(card_header_labels):
            item = QTableWidgetItem(label)
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if label == "Yellow":
                item.setForeground(QColor("#FFFF00"))
            elif label == "Red":
                item.setForeground(QColor("#FF0000"))
            else:
                item.setForeground(QColor(CONFIG["colors"]["text"]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.away_card_table.setHorizontalHeaderItem(col, item)
        header = self.away_card_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.setStretchLastSection(False)
        self.away_card_table.verticalHeader().setVisible(False)
        self.away_card_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )

        # Away Card Table starts empty - rows will be added via + button

        # Add custom delegate for time column in both cards tables
        from PySide6.QtCore import QRegularExpression
        from PySide6.QtGui import QRegularExpressionValidator
        from PySide6.QtWidgets import QStyledItemDelegate

        class TimeColumnDelegate(QStyledItemDelegate):
            def createEditor(self, parent, option, index):
                editor = super().createEditor(parent, option, index)
                if editor:
                    editor.setFont(QFont("Verdana", 12))
                    # Use shared styling for time editors
                    editor.setStyleSheet(TIME_EDITOR_STYLE)
                    # Add validator to only allow numbers and colon (for time format)
                    # Pattern allows: digits and colon, max 6 chars (e.g., "104:56" or "90:00")
                    # This allows up to 5 digits plus colon symbol, no alphabets
                    regex = QRegularExpression(r"^[0-9:]{0,6}$")
                    validator = QRegularExpressionValidator(regex, editor)
                    editor.setValidator(validator)
                    # Also set max length to prevent too long input
                    editor.setMaxLength(6)
                return editor

            def setModelData(self, editor, model, index):
                """Format the input to MM:SS or MMM:SS format when 3, 4, or 5 digits are entered"""
                text = editor.text().strip()

                # Remove any existing colons to get just digits
                digits_only = text.replace(":", "")

                # Format based on number of digits
                if len(digits_only) == 3:
                    # Format as 0X:XX (e.g., "345" -> "03:45")
                    minutes = digits_only[0].zfill(2)
                    seconds = digits_only[1:3].zfill(2)
                    formatted_text = f"{minutes}:{seconds}"
                elif len(digits_only) == 4:
                    # Format as XX:XX (e.g., "2345" -> "23:45")
                    minutes = digits_only[0:2]
                    seconds = digits_only[2:4]
                    formatted_text = f"{minutes}:{seconds}"
                elif len(digits_only) == 5:
                    # Format as XXX:XX (e.g., "10456" -> "104:56")
                    minutes = digits_only[0:3]
                    seconds = digits_only[3:5]
                    formatted_text = f"{minutes}:{seconds}"
                elif ":" in text:
                    # Already has colon, use as is (but ensure proper format)
                    parts = text.split(":")
                    if len(parts) == 2:
                        minutes = parts[0]
                        seconds = parts[1].zfill(2)
                        formatted_text = f"{minutes}:{seconds}"
                    else:
                        formatted_text = text
                else:
                    # Use text as is if it doesn't match patterns
                    formatted_text = text

                # Set the formatted text to the model
                model.setData(index, formatted_text, Qt.ItemDataRole.EditRole)

        time_delegate = TimeColumnDelegate()
        self.home_card_table.setItemDelegateForColumn(0, time_delegate)
        self.away_card_table.setItemDelegateForColumn(0, time_delegate)

    def deploy_selected_cards(self, table, team):
        """Deploy all selected card rows from the given table."""
        selected_rows = []
        for row in range(table.rowCount()):
            if not table.isRowHidden(row):
                select_widget = table.cellWidget(row, 5)
                if select_widget:
                    select_cb = select_widget.findChild(QCheckBox)
                    if select_cb and select_cb.isChecked():
                        time_item = table.item(row, 0)
                        num_item = table.item(row, 1)
                        name_widget = table.cellWidget(row, 2)
                        time = time_item.text() if time_item else "00:00"
                        num = num_item.text() if num_item else ""
                        name = name_widget.text() if name_widget else "Select Player"
                        selected_rows.append(
                            {
                                "row": row,
                                "time": time,
                                "num": num,
                                "name": name,
                                "team": team,
                            }
                        )
        if selected_rows:
            print(f"Deploying {len(selected_rows)} selected cards for {team}:")
            for item in selected_rows:
                print(
                    f"  - Row {item['row'] + 1}: {item['time']} | #{item['num']} | {item['name']}"
                )
        else:
            print(f"No cards selected for deployment for {team}")
        # Add Select checkboxes to Away Card Table
        for row in range(self.away_card_table.rowCount()):
            select_cb = QCheckBox()
            select_cb.setStyleSheet("""
                QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; }
                QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }
            """)
            select_widget = QWidget()
            select_widget.setStyleSheet("border: 0px;")
            select_layout = QHBoxLayout(select_widget)
            select_layout.addWidget(select_cb)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_layout.setContentsMargins(0, 0, 0, 0)
            self.away_card_table.setCellWidget(row, 5, select_widget)

    def _initialize_card_table(self, table, team_type):
        """Initialize card table with proper structure from Substituted.py"""
        from PySide6.QtWidgets import QButtonGroup, QCheckBox, QHBoxLayout

        # Initialize Card Table (adapted from Substituted.py)
        for row in range(table.rowCount()):
            time_item = QTableWidgetItem("00:00")
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            time_item.setFont(QFont("Verdana", 12))
            table.setItem(row, 0, time_item)

            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(row, 1, num_item)

            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_default"]};
                    color: {CONFIG["colors"]["text"]};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            name_btn.clicked.connect(
                lambda checked, r=row: self.show_card_player_list(table, r, team_type)
            )
            table.setCellWidget(row, 2, name_btn)

            # Position column removed - skip column 3

            # Yellow card checkbox
            card_group = QButtonGroup(table)
            yellow_cb = QCheckBox()
            yellow_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FFFF00;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            yellow_cb.setEnabled(False)  # Disable initially
            card_group.addButton(yellow_cb)
            # Connect to statistics when enabled
            yellow_cb.stateChanged.connect(
                lambda state,
                t=team_type,
                r=row,
                tbl=table: self.on_yellow_card_changed(state, t, r, tbl)
            )
            yellow_widget = QWidget()
            yellow_widget.setStyleSheet("border: 0px;")
            yellow_layout = QHBoxLayout(yellow_widget)
            yellow_layout.addWidget(yellow_cb)
            yellow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            yellow_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(
                row, 3, yellow_widget
            )  # Yellow moved from column 4 to 3

            # Red card checkbox
            red_cb = QCheckBox()
            red_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            red_cb.setEnabled(False)  # Disable initially
            card_group.addButton(red_cb)
            # Connect to statistics when enabled
            red_cb.stateChanged.connect(
                lambda state, t=team_type, r=row, tbl=table: self.on_red_card_changed(
                    state, t, r, tbl
                )
            )
            red_widget = QWidget()
            red_widget.setStyleSheet("border: 0px;")
            red_layout = QHBoxLayout(red_widget)
            red_layout.addWidget(red_cb)
            red_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            red_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 4, red_widget)  # Red moved from column 5 to 4

            # Select checkbox (new column 5)
            select_cb = QCheckBox()
            select_cb.setStyleSheet("""
                QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; }
                QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }
            """)
            select_widget = QWidget()
            select_widget.setStyleSheet("border: 0px;")
            select_layout = QHBoxLayout(select_widget)
            select_layout.addWidget(select_cb)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 5, select_widget)

            # Lock checkbox (now column 6)
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            lock_cb.setEnabled(False)  # Disable initially
            lock_cb.stateChanged.connect(
                lambda state, r=row: self.toggle_card_row_lock(table, r, state)
            )
            lock_widget = QWidget()
            lock_widget.setStyleSheet("border: 0px;")
            lock_layout = QHBoxLayout(lock_widget)
            lock_layout.addWidget(lock_cb)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 6, lock_widget)

            # Reset button (now column 7)
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_danger"]};
                    color: white;
                    border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            reset_btn.setProperty("table", table)
            reset_btn.clicked.connect(self._on_cards_reset_clicked)
            table.setCellWidget(row, 7, reset_btn)

        # Hide all rows except the first one initially
        for row in range(1, table.rowCount()):
            table.hideRow(row)

    def show_card_player_list(self, table, row, team_type):
        """Show card player list popup styled and structured like Substituted.py cards popup."""
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QColor, QFont
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QHeaderView,
                QMessageBox,
                QPushButton,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
            )

            if not self.match_created:
                QMessageBox.warning(
                    None,
                    "No Match Created",
                    "Please create a match in the Match Setup tab first before selecting players.",
                )
                return

            # Check if row is locked
            lock_widget = table.cellWidget(row, 6)  # Lock column in cards table
            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb and lock_cb.isChecked():
                    QMessageBox.warning(
                        None,
                        "Row Locked",
                        f"Row {row + 1} is locked and cannot be edited.",
                    )
                    return

            # Get team data
            team_data = (
                getattr(self, "home_team_data", None)
                if team_type == "home"
                else getattr(self, "away_team_data", None)
            )
            team_label = "Home Team" if team_type == "home" else "Away Team"

            if not team_data or not isinstance(team_data, dict):
                QMessageBox.warning(
                    None,
                    "No Data",
                    f"No team data loaded for {team_label}. Please load team data in Match Setup tab.",
                )
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Select Card Recipient for {team_label}")
            dialog.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #28293A, stop:1 #1e1e1e);
                    color: #B0B4BB;
                }
            """)
            dialog.setFixedSize(620, 900)

            layout = QVBoxLayout(dialog)

            # Player table: Name, Number, Position, Y, R
            player_table = QTableWidget(dialog)
            player_table.setColumnCount(5)
            player_table.setHorizontalHeaderLabels(
                ["Name", "Number", "Position", "Y", "R"]
            )
            player_table.setStyleSheet("""
                QTableWidget {
                    background: transparent;
                    border: 1px solid #374151;
                    gridline-color: #374151;
                    selection-background-color: #22c55e;
                    selection-color: #000000;
                    font-size: 14px;
                }
                QHeaderView::section {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    color: #10b981;
                    padding: 8px 6px;
                    border: 1px solid #374151;
                    font-weight: 700;
                    font-size: 14px;
                }
                QTableWidget::item {
                    padding: 6px 4px;
                    border-bottom: 1px solid #374151;
                }
                QTableWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white;
                    font-weight: bold;
                }
            """)

            header = player_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)  # name
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # number
            header.setSectionResizeMode(2, QHeaderView.Fixed)  # position
            header.setSectionResizeMode(3, QHeaderView.Fixed)  # yellow
            header.setSectionResizeMode(4, QHeaderView.Fixed)  # red

            player_table.setColumnWidth(1, 80)
            player_table.setColumnWidth(2, 100)
            player_table.setColumnWidth(3, 40)
            player_table.setColumnWidth(4, 40)

            player_table.verticalHeader().setVisible(False)
            player_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            player_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            player_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            layout.addWidget(player_table)

            # Build card counts from current table (by jersey number for players, by name for officials)
            card_counts_by_number = {}  # jersey_no -> {yellow, red} (for players)
            card_counts_by_name = {}  # name -> {yellow, red} (for officials without jersey numbers)

            for r in range(table.rowCount()):
                num_item = table.item(r, 1)
                jersey_no = num_item.text().strip() if num_item else ""
                name_btn = table.cellWidget(r, 2)
                name = name_btn.text().strip() if name_btn else ""

                if not name or name == "Select Player":
                    continue

                # Players have jersey numbers, officials don't
                if jersey_no:
                    # This is a player - count by jersey number
                    if jersey_no not in card_counts_by_number:
                        card_counts_by_number[jersey_no] = {"yellow": 0, "red": 0}
                    yellow_widget = table.cellWidget(r, 3)  # Yellow column
                    red_widget = table.cellWidget(r, 4)  # Red column
                    if yellow_widget:
                        ycb = yellow_widget.findChild(QCheckBox)
                        if ycb and ycb.isChecked():
                            card_counts_by_number[jersey_no]["yellow"] += 1
                    if red_widget:
                        rcb = red_widget.findChild(QCheckBox)
                        if rcb and rcb.isChecked():
                            card_counts_by_number[jersey_no]["red"] += 1
                else:
                    # This is an official - count by name
                    if name not in card_counts_by_name:
                        card_counts_by_name[name] = {"yellow": 0, "red": 0}
                    yellow_widget = table.cellWidget(r, 3)
                    red_widget = table.cellWidget(r, 4)
                    if yellow_widget:
                        ycb = yellow_widget.findChild(QCheckBox)
                        if ycb and ycb.isChecked():
                            card_counts_by_name[name]["yellow"] += 1
                    if red_widget:
                        rcb = red_widget.findChild(QCheckBox)
                        if rcb and rcb.isChecked():
                            card_counts_by_name[name]["red"] += 1

            # Promote pairs of yellow cards to red count in the popup view (per player/official)
            for jersey_no, counts in card_counts_by_number.items():
                try:
                    counts["red"] += counts.get("yellow", 0) // 2
                except Exception:
                    pass
            for name, counts in card_counts_by_name.items():
                try:
                    counts["red"] += counts.get("yellow", 0) // 2
                except Exception:
                    pass

            # Prepare players list - separate playing 11 from substitutes
            all_players = team_data.get("players", [])
            playing_11 = team_data.get("playing_11", [])

            # Create a set of playing 11 player IDs for quick lookup
            playing_11_ids = set()
            for p11 in playing_11:
                if isinstance(p11, dict):
                    playing_11_ids.add(p11.get("id", ""))

            # Separate players into playing 11 and substitutes
            playing_players = []
            substitute_players = []
            for p in all_players:
                if p.get("id", "") in playing_11_ids or p.get("selected", False):
                    playing_players.append(p)
                else:
                    substitute_players.append(p)

            # Sort both lists by jersey number if possible
            try:
                playing_players = sorted(
                    playing_players, key=lambda x: int(x.get("jersey_number", 0))
                )
                substitute_players = sorted(
                    substitute_players, key=lambda x: int(x.get("jersey_number", 0))
                )
            except Exception:
                pass

            # Compute number of officials
            official_keys = [
                "owner",
                "manager",
                "technical_director",
                "head_coach",
                "gk_coach",
                "asst._coach",
            ]
            num_officials = sum(1 for key in official_keys if team_data.get(key))

            # Calculate total rows: playing_11 + substitutes_separator + substitutes + officials_separator + officials
            num_substitutes = len(substitute_players)
            total_rows = len(playing_players)
            total_rows += (
                1 if num_substitutes > 0 else 0
            ) + num_substitutes  # Substitutes separator + substitutes
            total_rows += (
                1 if num_officials > 0 else 0
            ) + num_officials  # Officials separator + officials
            player_table.setRowCount(total_rows)

            row_idx = 0
            row_idx = 0
            # Populate playing 11 players
            for p in playing_players:
                name = p.get("full_name", "")
                number = str(p.get("jersey_number", ""))
                position = p.get("position", "")
                y_count = card_counts_by_number.get(number, {"yellow": 0})["yellow"]
                r_count = card_counts_by_number.get(number, {"red": 0})["red"]

                name_item = QTableWidgetItem(name)
                name_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                number_item = QTableWidgetItem(number)
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                position_item = QTableWidgetItem(position)
                position_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                y_item = QTableWidgetItem(str(y_count) if y_count > 0 else "")
                y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                r_item = QTableWidgetItem(str(r_count) if r_count > 0 else "")
                r_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Color coding
                if number in card_counts_by_number:
                    if r_count > 0:
                        for it in (
                            name_item,
                            number_item,
                            position_item,
                            y_item,
                            r_item,
                        ):
                            it.setForeground(QColor("#FF0000"))
                    elif y_count > 0:
                        for it in (
                            name_item,
                            number_item,
                            position_item,
                            y_item,
                            r_item,
                        ):
                            it.setForeground(QColor("#FFFF00"))
                    if y_count > 0:
                        y_item.setForeground(QColor("#FFFF00"))
                    if r_count > 0:
                        r_item.setForeground(QColor("#FF0000"))
                    # Disable if limits reached (double yellow or direct red)
                    if r_count >= 1 or y_count >= 2:
                        for it in (
                            name_item,
                            number_item,
                            position_item,
                            y_item,
                            r_item,
                        ):
                            it.setFlags(Qt.ItemFlag.NoItemFlags)

                player_table.setItem(row_idx, 0, name_item)
                player_table.setItem(row_idx, 1, number_item)
                player_table.setItem(row_idx, 2, position_item)
                player_table.setItem(row_idx, 3, y_item)
                player_table.setItem(row_idx, 4, r_item)
                row_idx += 1

            # Substitutes separator
            if num_substitutes > 0:
                sep = QTableWidgetItem("Substitutes")
                sep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                sep.setFlags(Qt.ItemFlag.ItemIsSelectable)
                sep.setBackground(QColor("#1e1e1e"))
                sep.setForeground(QColor("#FFFFFF"))
                player_table.setItem(row_idx, 0, sep)
                player_table.setSpan(row_idx, 0, 1, 5)
                row_idx += 1

                # Populate substitute players
                for p in substitute_players:
                    name = p.get("full_name", "")
                    number = str(p.get("jersey_number", ""))
                    position = p.get("position", "")
                    y_count = card_counts_by_number.get(number, {"yellow": 0})["yellow"]
                    r_count = card_counts_by_number.get(number, {"red": 0})["red"]

                    name_item = QTableWidgetItem(name)
                    name_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                    number_item = QTableWidgetItem(number)
                    number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    position_item = QTableWidgetItem(position)
                    position_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    y_item = QTableWidgetItem(str(y_count) if y_count > 0 else "")
                    y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    r_item = QTableWidgetItem(str(r_count) if r_count > 0 else "")
                    r_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Color coding
                    if number in card_counts_by_number:
                        if r_count > 0:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setForeground(QColor("#FF0000"))
                        elif y_count > 0:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setForeground(QColor("#FFFF00"))
                        if y_count > 0:
                            y_item.setForeground(QColor("#FFFF00"))
                        if r_count > 0:
                            r_item.setForeground(QColor("#FF0000"))
                        # Disable if limits reached (double yellow or direct red)
                        if r_count >= 1 or y_count >= 2:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setFlags(Qt.ItemFlag.NoItemFlags)

                    player_table.setItem(row_idx, 0, name_item)
                    player_table.setItem(row_idx, 1, number_item)
                    player_table.setItem(row_idx, 2, position_item)
                    player_table.setItem(row_idx, 3, y_item)
                    player_table.setItem(row_idx, 4, r_item)
                    row_idx += 1

            # Officials separator
            if num_officials > 0:
                sep = QTableWidgetItem("Officials")
                sep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                sep.setFlags(Qt.ItemFlag.ItemIsSelectable)
                sep.setBackground(QColor("#1e1e1e"))
                sep.setForeground(QColor("#FFFFFF"))
                player_table.setItem(row_idx, 0, sep)
                player_table.setSpan(row_idx, 0, 1, 5)
                row_idx += 1
                sent_off_officials = self.sent_off_officials.get(team_type, set())
                # Populate officials
                for key in official_keys:
                    official_name = team_data.get(key)
                    if not official_name:
                        continue
                    y_count = card_counts_by_name.get(official_name, {"yellow": 0})[
                        "yellow"
                    ]
                    r_count = card_counts_by_name.get(official_name, {"red": 0})["red"]
                    name_item = QTableWidgetItem(official_name)
                    name_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                    number_item = QTableWidgetItem("")
                    number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    position_item = QTableWidgetItem(key.capitalize().replace("_", " "))
                    position_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    y_item = QTableWidgetItem(str(y_count) if y_count > 0 else "")
                    y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    r_item = QTableWidgetItem(str(r_count) if r_count > 0 else "")
                    r_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if official_name in card_counts_by_name:
                        if r_count > 0:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setForeground(QColor("#FF0000"))
                        elif y_count > 0:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setForeground(QColor("#FFFF00"))
                        if y_count > 0:
                            y_item.setForeground(QColor("#FFFF00"))
                        if r_count > 0:
                            r_item.setForeground(QColor("#FF0000"))
                        if r_count >= 1 or y_count >= 2:
                            for it in (
                                name_item,
                                number_item,
                                position_item,
                                y_item,
                                r_item,
                            ):
                                it.setFlags(Qt.ItemFlag.NoItemFlags)

                    if official_name in sent_off_officials:
                        tooltip = "Sent off — official is no longer available."
                        for it in (
                            name_item,
                            number_item,
                            position_item,
                            y_item,
                            r_item,
                        ):
                            it.setForeground(QColor("#FF0000"))
                            it.setFlags(Qt.ItemFlag.NoItemFlags)
                            it.setToolTip(tooltip)

                    player_table.setItem(row_idx, 0, name_item)
                    player_table.setItem(row_idx, 1, number_item)
                    player_table.setItem(row_idx, 2, position_item)
                    player_table.setItem(row_idx, 3, y_item)
                    player_table.setItem(row_idx, 4, r_item)
                    row_idx += 1

            # Selection handlers
            def apply_selection():
                selected = player_table.selectedIndexes()
                if not selected:
                    dialog.reject()
                    return
                sel_row = selected[0].row()
                # Ignore separator rows
                item0 = player_table.item(sel_row, 0)
                if item0 and item0.text() in [
                    "Substituted",
                    "Substitutes",
                    "Officials",
                ]:
                    dialog.reject()
                    return

                name = (
                    player_table.item(sel_row, 0).text()
                    if player_table.item(sel_row, 0)
                    else ""
                )
                number = (
                    player_table.item(sel_row, 1).text()
                    if player_table.item(sel_row, 1)
                    else ""
                )
                position = (
                    player_table.item(sel_row, 2).text()
                    if player_table.item(sel_row, 2)
                    else ""
                )

                # Update target table like Substituted.py
                name_btn = table.cellWidget(row, 2)
                if name_btn:
                    name_btn.setText(name)
                num_item = table.item(row, 1)
                if num_item:
                    num_item.setText(number)
                    num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                pos_item = table.item(row, 3) if table.columnCount() > 3 else None
                if pos_item is not None:
                    pos_item.setText(position)
                    pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Enable Lock, Yellow, Red
                lock_widget = table.cellWidget(row, 6)
                yellow_widget = table.cellWidget(row, 3)
                red_widget = table.cellWidget(row, 4)
                if lock_widget:
                    lcb = lock_widget.findChild(QCheckBox)
                    if lcb:
                        lcb.setEnabled(True)
                if yellow_widget:
                    ycb = yellow_widget.findChild(QCheckBox)
                    if ycb:
                        ycb.setEnabled(True)
                if red_widget:
                    rcb = red_widget.findChild(QCheckBox)
                    if rcb:
                        rcb.setEnabled(True)

                # Update time from running clock
                time_item = table.item(row, 0)
                if time_item:
                    time_item.setText(self.get_current_time_text())

                # Optionally update visibility/stats
                if hasattr(self, "update_card_stats"):
                    self.update_card_stats(team_type)

                dialog.accept()

            player_table.doubleClicked.connect(lambda: apply_selection())

            # Buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            ok_button.setFont(QFont("Verdana", 14))
            ok_button.setFixedHeight(44)
            ok_button.setMinimumWidth(120)
            ok_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            ok_button.clicked.connect(apply_selection)
            button_layout.addWidget(ok_button)

            cancel_button = QPushButton("Cancel")
            cancel_button.setFont(QFont("Verdana", 14))
            cancel_button.setFixedHeight(44)
            cancel_button.setMinimumWidth(120)
            cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            print(f"Error in show_card_player_list: {e}")

    def set_selected_card_player(self, table, row, player, team_type):
        """Set the selected player in the cards table"""
        try:
            # Update player name button
            name_btn = table.cellWidget(row, 2)
            if name_btn:
                name_btn.setText(player.get("full_name", "Unknown"))

            # Update jersey number
            num_item = table.item(row, 1)
            if num_item:
                num_item.setText(str(player.get("jersey_number", "")))

            # Update time (use same source as scorer panel)
            time_item = table.item(row, 0)
            if time_item:
                ct = self.get_current_time_text()
                try:
                    print(f"DEBUG set_selected_card_player: row={row}, time={ct}")
                except Exception:
                    pass
                time_item.setText(ct)

            # Enable checkboxes when player is selected
            lock_widget = table.cellWidget(row, 6)
            yellow_widget = table.cellWidget(row, 3)
            red_widget = table.cellWidget(row, 4)

            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb:
                    lock_cb.setEnabled(True)
            if yellow_widget:
                yellow_cb = yellow_widget.findChild(QCheckBox)
                if yellow_cb:
                    yellow_cb.setEnabled(True)
                    # Note: Connection already established in _initialize_card_table()
            if red_widget:
                red_cb = red_widget.findChild(QCheckBox)
                if red_cb:
                    red_cb.setEnabled(True)
                    # Note: Connection already established in _initialize_card_table()

        except Exception as e:
            print(f"Error setting selected card player: {e}")

    def toggle_card_row_lock(self, table, row, state):
        """Toggle lock state for card table row"""
        is_locked = state == Qt.CheckState.Checked.value

        # Disable/enable widgets based on lock state
        # Time column (0) - should remain editable when unlocked
        time_item = table.item(row, 0)
        if time_item:
            if is_locked:
                time_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            else:
                time_item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsEditable
                )

        # Number column (1) - not editable
        num_item = table.item(row, 1)
        if num_item:
            if is_locked:
                num_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            else:
                num_item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )

        for col in [2, 3, 4, 7]:  # Name, Yellow, Red, Reset (adjusted indices)
            widget = table.cellWidget(row, col)
            if widget:
                widget.setEnabled(not is_locked)
        export_widget = table.cellWidget(row, 5)
        if export_widget:
            cb = export_widget.findChild(QCheckBox)
            if cb:
                cb.setEnabled(not is_locked)

    def reset_card_row(self, table, row):
        """Reset a card table row to default values but preserve time and hide rows below"""
        try:
            # Check if row is locked (column 6)
            lock_widget = table.cellWidget(row, 6)
            if lock_widget:
                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb and lock_cb.isChecked():
                    QMessageBox.warning(
                        self,
                        "Row Locked",
                        f"Row {row + 1} is locked and cannot be reset.",
                    )
                    return

            # Preserve time - don't reset it
            # Reset other data
            num_item = table.item(row, 1)
            if num_item:
                num_item.setText("")

            # Reset name button
            name_btn = table.cellWidget(row, 2)
            if name_btn:
                name_btn.setText("Select Player")

                # Reset checkboxes (Yellow, Red, Lock)
            for col in [3, 4, 6]:  # Yellow, Red, Lock
                widget = table.cellWidget(row, col)
                if widget:
                    cb = widget.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(False)
                        # Enable yellow/red checkboxes, disable lock checkbox
                        cb.setEnabled(True if col in [3, 4] else False)

            # Hide all rows below this one instead of deleting them
            total_rows = table.rowCount()
            for r in range(row + 1, total_rows):
                table.hideRow(r)

            print(
                f"Reset card row {row} to default (preserved time, hidden rows below)"
            )
            # After resetting a row, recompute card totals and fouls
            try:
                team = None
                if table == self.home_cards_table:
                    team = "home"
                elif table == self.away_cards_table:
                    team = "away"

                if team:
                    self.update_card_totals(team)
                    self.update_fouls_display(team)
            except Exception as e:
                print(f"Error updating card totals after reset: {e}")

        except Exception as e:
            print("Error resetting card row")

    # Reset button moved to toolbar in main window

    def reset_match(self):
        """Reset the match state to initial match-created state."""
        try:
            # Reset basic match state
            self.seconds = 0
            self.home_goals = 0
            self.away_goals = 0
            self.home_goal_label.setText("0")
            self.away_goal_label.setText("0")

            self.update_timer_display()
            self.stop_timer()
            self.min_value.setValue(0)
            self.second_value.setValue(0)
            self.extra_time_enabled = False
            self.extra_time_minutes = 0

            # Reset possession tracking
            self.home_ball_control_time = 0
            self.away_ball_control_time = 0
            self.current_possession = None
            self._suppress_possession_highlight_once = True
            try:
                self.update_team_panel_borders()
            except Exception:
                pass

            # Reset possession button text back to "Kickoff" and reapply styling
            if hasattr(self, "possession_toggle_btn"):
                self.possession_toggle_btn.setText("Kickoff")
                self._apply_possession_button_style("neutral")

            # Reset statistics data
            for key in self.stats_data:
                self.stats_data[key] = 0

            # Reset cards tables
            if hasattr(self, "home_card_table"):
                for row in range(self.home_card_table.rowCount()):
                    self.reset_card_row(self.home_card_table, row)
                    if row > 0:  # Hide all rows except first
                        self.home_card_table.hideRow(row)

            if hasattr(self, "away_card_table"):
                for row in range(self.away_card_table.rowCount()):
                    self.reset_card_row(self.away_card_table, row)
                    if row > 0:  # Hide all rows except first
                        self.away_card_table.hideRow(row)

            # Reset scorer panels and their tables
            if hasattr(self, "home_scorer_panel"):
                print("DEBUG reset_match: clearing home scorer")
                self.home_scorer_panel.previous_goal_count = 0
                # Hide all rows initially (match-created state)
                for r in range(self.home_scorer_panel.scorer_table.rowCount()):
                    try:
                        self.home_scorer_panel.scorer_table.hideRow(r)
                    except Exception:
                        pass
                # Reset all scorer table rows
                for row in range(self.home_scorer_panel.scorer_table.rowCount()):
                    self.home_scorer_panel.reset_scorer_row(row)

            if hasattr(self, "away_scorer_panel"):
                print("DEBUG reset_match: clearing away scorer")
                self.away_scorer_panel.previous_goal_count = 0
                # Hide all rows initially (match-created state)
                for r in range(self.away_scorer_panel.scorer_table.rowCount()):
                    try:
                        self.away_scorer_panel.scorer_table.hideRow(r)
                    except Exception:
                        pass
                # Reset all scorer table rows
                for row in range(self.away_scorer_panel.scorer_table.rowCount()):
                    self.away_scorer_panel.reset_scorer_row(row)

            # Reset stats widgets and update display
            if hasattr(self, "stats_widgets"):
                for stat_key, widgets in self.stats_widgets.items():
                    if stat_key == "possession_time":
                        widgets["home_value"].setText("00:00")
                        widgets["away_value"].setText("00:00")
                    elif stat_key == "possession":
                        widgets["home_value"].setText("50")
                        widgets["away_value"].setText("50")
                    else:
                        widgets["home_value"].setText("0")
                        widgets["away_value"].setText("0")

            # Reset extra time components
            if hasattr(self, "extra_time_spin"):
                self.extra_time_spin.setValue(0)
            if hasattr(self, "extra_time_check"):
                self.extra_time_check.setChecked(False)
            if hasattr(self, "extra_time_value_label"):
                self.extra_time_value_label.setText("+0")
                self.extra_time_value_label.setVisible(False)

            # Reset radio button to current time
            if hasattr(self, "radio_current_time"):
                self.radio_current_time.setChecked(True)

            # Reset header styles to default
            if hasattr(self, "stats_home_header_label"):
                self.stats_home_header_label.setStyleSheet(
                    self.stats_header_default_style
                )
            if hasattr(self, "stats_away_header_label"):
                self.stats_away_header_label.setStyleSheet(
                    self.stats_header_default_style
                )

            # Ensure scorer visibility matches goals (0) strictly
            self._ensure_scorer_panel_initialized("home")
            self._ensure_scorer_panel_initialized("away")
            self._debug_dump_scorer_rows("home")
            self._debug_dump_scorer_rows("away")
            print("DEBUG reset_match: end")

            # Update all stats displays to reflect the reset values
            self.update_all_stats_displays()

            print("Match reset completed successfully")

        except Exception as e:
            print(f"Error in reset_match: {str(e)}")

    def update_all_stats_displays(self):
        """Update all stats displays to show current values."""
        try:
            # Update all stat displays for both teams
            for stat_key in self.stats_data:
                self.update_stat_display(stat_key, "home")
                self.update_stat_display(stat_key, "away")

            # Update possession times display
            self.update_possession_times()

        except Exception as e:
            print(f"Error updating stats displays: {str(e)}")

    def _ensure_scorer_panel_initialized(self, side: str):
        """Ensure scorer table exists with rows so row visibility can change with goals."""
        try:
            panel = self.home_scorer_panel if side == "home" else self.away_scorer_panel
            if not panel or not hasattr(panel, "scorer_table"):
                print(f"DEBUG ensure_scorer[{side}]: panel/table missing")
                return
            if panel.scorer_table.rowCount() == 0:
                print(f"DEBUG ensure_scorer[{side}]: rowCount==0 -> reinitialize")
                if hasattr(panel, "_initialize_table"):
                    panel._initialize_table()
                else:
                    panel.scorer_table.setRowCount(30)
                # hide all rows after reinit (match-created)
                for r in range(panel.scorer_table.rowCount()):
                    try:
                        panel.scorer_table.hideRow(r)
                    except Exception:
                        pass
        except Exception as e:
            print(f"DEBUG ensure_scorer error [{side}]: {e}")

    def _debug_dump_scorer_rows(self, side: str):
        """Print a compact visibility snapshot of scorer rows for debugging."""
        try:
            panel = self.home_scorer_panel if side == "home" else self.away_scorer_panel
            if not hasattr(panel, "scorer_table"):
                print(f"DEBUG scorer[{side}]: no table")
                return
            count = panel.scorer_table.rowCount()
            snapshot = "".join(
                "1" if not panel.scorer_table.isRowHidden(r) else "0"
                for r in range(min(10, count))
            )
            print(
                f"DEBUG scorer[{side}] rows={count} visible(first10)={snapshot} goals={self.home_goals if side == 'home' else self.away_goals}"
            )
        except Exception as e:
            print(f"DEBUG scorer dump error [{side}]: {e}")

    def _create_extra_timer_panel(self):
        """Create extra timer panel exactly like reference"""
        # Extra Timer Section Panel (aligned to Match Statistics width and center)
        extra_timer_panel = QWidget(self)
        extra_timer_panel.setGeometry(670, 345, 580, 113)
        extra_timer_panel.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 16px;
            }}
        """)

        # Timer Naming Section
        self.radio_current_time = QRadioButton("CURRENT TIME", extra_timer_panel)
        self.radio_current_time.setGeometry(10, 8, 139, 24)
        self.radio_current_time.setFont(QFont("Verdana", 11))
        self.radio_current_time.setChecked(True)

        self.radio_half_time = QRadioButton("HALF TIME", extra_timer_panel)
        self.radio_half_time.setGeometry(173, 8, 110, 24)
        self.radio_half_time.setFont(QFont("Verdana", 11))

        self.radio_full_time = QRadioButton("FULL TIME", extra_timer_panel)
        self.radio_full_time.setGeometry(310, 8, 110, 24)
        self.radio_full_time.setFont(QFont("Verdana", 11))

        self.radio_extra_time = QRadioButton("EXTRA TIME", extra_timer_panel)
        self.radio_extra_time.setGeometry(450, 8, 120, 24)
        self.radio_extra_time.setFont(QFont("Verdana", 11))

        self.extra_time_label = QLabel("ET", extra_timer_panel)
        self.extra_time_label.setGeometry(2, 60, 90, 25)
        self.extra_time_label.setFont(QFont("Verdana", 17, QFont.Weight.Bold))
        self.extra_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.extra_time_label.setStyleSheet(f"""
            QLabel {{
                color: {CONFIG["colors"]["text"]};
                background: transparent;
                border: none;
            }}
        """)

        self.extra_time_spin = CustomSpinBox(
            extra_timer_panel,
            font=QFont("Verdana", 10),
            range_min=0,
            range_max=30,
            width=53,
            height=38,
            buttons_on_right=True,
            show_buttons=False,
        )
        # Respect the spinbox's intrinsic dimensions to prevent clipping
        self.extra_time_spin.setGeometry(70, 55, 53, 38)

        self.btn_extra_time = ModernButton(
            "Apply", "success", extra_timer_panel, font_size=14
        )
        self.btn_extra_time.setGeometry(170, 55, 80, 43)
        # Force font size application
        self.btn_extra_time.setFont(QFont("Verdana", 14, QFont.Weight.Bold))

        # Position RESET ET safely inside the panel (avoid clipping on the right)
        self.btn_reset_timer = ModernButton(
            "RESET ET", "danger", extra_timer_panel, font_size=12.5
        )
        self.btn_reset_timer.setGeometry(438, 59, 120, 40)

        # Add proper styling for radio buttons
        radio_style = f"""
            QRadioButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                color: {CONFIG["colors"]["text"]};
                font-size: 12px;
                font-weight: normal;
                border-radius: 6px;
                border: 1px solid {CONFIG["colors"]["border"]};
                padding: 5px;
            }}
            QRadioButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["hover"]}, stop:1 #2563eb);
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid {CONFIG["colors"]["border"]};
                background: {CONFIG["colors"]["panel"]};
            }}
            QRadioButton::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["button_danger"]}, stop:1 #b91c1c);
                border: 2px solid {CONFIG["colors"]["text"]};
            }}
        """

        # Apply styling to radio buttons
        self.radio_current_time.setStyleSheet(radio_style)
        self.radio_half_time.setStyleSheet(radio_style)
        self.radio_full_time.setStyleSheet(radio_style)
        self.radio_extra_time.setStyleSheet(radio_style)

        # Create button group and connect signals
        self.time_type_group = QButtonGroup(self)
        self.time_type_group.addButton(self.radio_current_time)
        self.time_type_group.addButton(self.radio_half_time)
        self.time_type_group.addButton(self.radio_full_time)
        self.time_type_group.addButton(self.radio_extra_time)

        # Connect radio button signals
        self.radio_current_time.toggled.connect(self.update_time_type)
        self.radio_half_time.toggled.connect(self.update_time_type)
        self.radio_full_time.toggled.connect(self.update_time_type)
        self.radio_extra_time.toggled.connect(self.update_time_type)

        # Connect button animations
        for radio in [
            self.radio_current_time,
            self.radio_half_time,
            self.radio_full_time,
            self.radio_extra_time,
        ]:
            animator = FontSizeAnimator(radio, 12)
            self.button_animators[radio] = animator
            radio.clicked.connect(lambda: self.animate_button_click(radio))

        # Connect extra timer functionality
        animator_extra_time = FontSizeAnimator(self.btn_extra_time, 12)
        self.button_animators[self.btn_extra_time] = animator_extra_time
        self.btn_extra_time.clicked.connect(
            lambda: self.animate_button_click(self.btn_extra_time)
        )
        self.btn_extra_time.clicked.connect(self.apply_extra_time)

        animator_reset_timer = FontSizeAnimator(self.btn_reset_timer, 12)
        self.button_animators[self.btn_reset_timer] = animator_reset_timer
        self.btn_reset_timer.clicked.connect(
            lambda: self.animate_button_click(self.btn_reset_timer)
        )
        self.btn_reset_timer.clicked.connect(self.reset_timer)

        # Add extra time components
        self.extra_time_value_label = ModernLabel("+0", "success", self, font_size=25)
        self.extra_time_value_label.setGeometry(1100, 40, 55, 34)
        self.extra_time_value_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.extra_time_value_label.setVisible(False)
        # Remove background styling
        self.extra_time_value_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {CONFIG["colors"]["text_success"]};
                font-size: 25px;
                font-weight: 600;
                letter-spacing: 0.025em;
                border: none;
            }}
        """)

        self.extra_time_check = QCheckBox("Show Extra Time", extra_timer_panel)
        self.extra_time_check.setGeometry(255, 59, 178, 40)
        self.extra_time_check.setFont(QFont("Verdana"))
        self.extra_time_check.setStyleSheet(f"""
            QCheckBox {{
                color: {CONFIG["colors"]["text"]};
                font-size: 14px;
                font-weight: normal;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 8px;
                padding: 2px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {CONFIG["colors"]["border"]};
                background: {CONFIG["colors"]["panel"]};
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["button_success"]}, stop:1 #047857);
            }}
        """)
        self.extra_time_check.stateChanged.connect(self.toggle_extra_time_label)

        # Add up/down buttons for extra time
        self.extra_time_up_button = ModernButton(
            "\u25b2", "primary", extra_timer_panel, font_size=12
        )
        # First set geometry on the UP button (the DOWN button is not created yet)
        self.extra_time_up_button.setGeometry(130, 52, 20, 20)
        self.extra_time_up_button.setFixedSize(25, 23)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.extra_time_up_button.clicked.connect(
            lambda: self.extra_time_spin.increment()
        )

        self.extra_time_down_button = ModernButton(
            "\u25bc", "primary", extra_timer_panel, font_size=12
        )
        self.extra_time_down_button.setGeometry(130, 76, 20, 20)
        self.extra_time_down_button.setFixedSize(25, 23)
        # Remove FontSizeAnimator to prevent arrow size changes
        self.extra_time_down_button.clicked.connect(
            lambda: self.extra_time_spin.decrement()
        )

    def _create_stats_panel(self):
        """Create match statistics panel exactly like reference"""
        # Match Statistics Panel
        stats_panel = QWidget(self)
        stats_panel.setGeometry(670, 465, 580, 480)
        stats_panel.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                border: 2px solid {CONFIG["colors"]["border"]};
            }}
        """)

        # Stats title with deploy button
        stats_title = ModernLabel(
            "MATCH STATISTICS", "heading", stats_panel, font_size=18
        )
        stats_title.setGeometry(20, 0, 545, 60)  # Reduced width for smaller panel
        stats_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Deploy button positioned within the title label boundary
        self.stats_deploy_button = QPushButton("DEPLOY", stats_panel)
        self.stats_deploy_button.setFont(QFont("Verdana", 14, QFont.Weight.Bold))
        # Nudge deploy button away from rounded border
        self.stats_deploy_button.setGeometry(470, 15, 90, 30)
        self.stats_deploy_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }}
        """)
        self.stats_deploy_button.clicked.connect(self.deploy_all_stats)
        self.stats_deploy_button.show()  # Explicitly show the button
        self.stats_deploy_button.raise_()  # Bring to front

        # Header row
        header_style = f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f2f30, stop:1 #1c1c1c);
                color: {CONFIG["colors"]["text"]};
                font-size: 14px;
                font-weight: 700;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """
        # Keep header styles for later dynamic highlighting
        self.stats_header_default_style = header_style
        self.stats_header_active_style = f"""
            QLabel {{
                background: {CONFIG["colors"]["button_danger"]};
                color: {CONFIG["colors"]["text"]};
                font-size: 14px;
                font-weight: 700;
                border: 1px solid {CONFIG["colors"]["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """

        # Compute dynamic width for the Stats column to occupy all middle space
        # Layout: |<-20->|[Home 140]|<-gap 20->|[Stats ?]|<-gap 20->|[Away 140]|<-20->|
        left_margin = 20
        right_margin = 20
        header_width = 140
        gap_between_columns = 20
        panel_width = stats_panel.geometry().width()
        # X for stats column begins after left header and gap
        # Adjust this value to shift the entire stats column left (negative) or right (positive)
        stat_x = 193  # Change this value, e.g., 193 + 10 = 203 (move right) or 193 - 10 = 183 (move left)
        # X for away header is aligned from the right margin
        # Adjust this value to shift the entire away team column left (negative) or right (positive)
        away_header_x = (
            panel_width - right_margin - header_width
        )  # Add offset here if needed, e.g., +10 or -10
        # Middle column width spans remaining space
        # Adjust this value to change the overall stats column width (affects header, button, and label container)
        stat_col_width = 200  # Change this value, e.g., 200 + 50 = 250 (wider) or 200 - 30 = 170 (narrower)

        home_header = ModernLabel("HOME TEAM", "subheading", stats_panel, font_size=14)
        home_header.setGeometry(25, 60, 140, 40)
        home_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_header.setStyleSheet(header_style)
        # Keep reference to allow dynamic rename when teams load
        self.stats_home_header_label = home_header

        stat_header = ModernLabel("STATISTICS", "subheading", stats_panel, font_size=14)
        stat_header.setGeometry(stat_x, 60, stat_col_width, 40)
        stat_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_header.setStyleSheet(header_style)

        # away_header_x already computed from panel width above
        away_header = ModernLabel("AWAY TEAM", "subheading", stats_panel, font_size=14)
        away_header.setGeometry(away_header_x, 60, 140, 40)
        away_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        away_header.setStyleSheet(header_style)
        # Keep reference to allow dynamic rename when teams load
        self.stats_away_header_label = away_header

        # Kickoff toggle button (center column)
        self.possession_toggle_btn = ModernButton(
            "Kickoff", "primary", stats_panel, font_size=12
        )
        # Place just under the headers, make it span the full stats column width
        # Adjust btn_width to change the Kickoff button width (default uses full stat_col_width)
        btn_width = stat_col_width  # Change this, e.g., stat_col_width - 20 (narrower) or stat_col_width + 10 (wider)
        btn_x = stat_x  # Adjust this to move just the kickoff button, e.g., stat_x + 5 or stat_x - 5
        self.possession_toggle_btn.setGeometry(btn_x, 105, btn_width, 30)
        self._apply_possession_button_style("neutral")
        animator_possession_toggle = FontSizeAnimator(self.possession_toggle_btn, 12)
        self.button_animators[self.possession_toggle_btn] = animator_possession_toggle
        self.possession_toggle_btn.clicked.connect(
            lambda: self.animate_button_click(self.possession_toggle_btn)
        )
        self.possession_toggle_btn.clicked.connect(self.toggle_possession)

        try:
            self.possession_toggle_btn.raise_()
        except Exception:
            pass

        # Initialize possession state holder if not present
        if not hasattr(self, "current_possession"):
            self.current_possession = None

        # Statistics rows data
        stats_rows = [
            ("", "possession_time", False, True),
            ("Goals", "goals", False, False),  # Remove spinner for goals
            ("Shots", "shots", True, False),
            ("Shots on Target", "shots_on_target", True, False),
            ("Possession", "possession", False, False),
            ("Fouls", "fouls", True, False),
            ("Yellow Cards", "yellow_cards", False, False),
            ("Red Cards", "red_cards", False, False),
            ("Offsides", "offsides", True, False),
            ("Corner", "corners", True, False),
        ]

        # Create statistics rows
        self.stats_widgets = {}
        row_height = 35
        start_y = 110

        for i, (label_text, stat_key, has_controls, is_possession) in enumerate(
            stats_rows
        ):
            y_pos = start_y + (i * row_height)

            if has_controls:
                home_dec = ModernButton("◄", "primary", stats_panel, font_size=16)
                home_dec.setGeometry(20, y_pos, 30, 30)
                animator_home_dec = FontSizeAnimator(home_dec, 16)
                self.button_animators[home_dec] = animator_home_dec
                home_dec.clicked.connect(
                    lambda checked, key=stat_key, team="home": self.safe_decrease_stat(
                        key, team
                    )
                )
                home_dec.clicked.connect(lambda: self.animate_button_click(home_dec))

                home_value = ModernLabel("0", "body", stats_panel, font_size=16)
                home_value.setGeometry(55, y_pos, 90, 30)
                home_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                home_value.setStyleSheet(f"""
                    QLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 16px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)

                home_inc = ModernButton("►", "primary", stats_panel, font_size=16)
                home_inc.setGeometry(150, y_pos, 30, 30)
                animator_home_inc = FontSizeAnimator(home_inc, 16)
                self.button_animators[home_inc] = animator_home_inc
                home_inc.clicked.connect(
                    lambda checked, key=stat_key, team="home": self.increase_stat(
                        key, team
                    )
                )
                home_inc.clicked.connect(lambda: self.animate_button_click(home_inc))

            elif is_possession:
                # Editable possession time (mm:ss) unlocked via context menu
                from PySide6.QtWidgets import QLineEdit

                home_time = QLineEdit("00:00", stats_panel)
                home_time.setGeometry(50, y_pos, 100, 30)
                home_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
                try:
                    home_time.setInputMask("00:00")
                except Exception:
                    pass
                home_time.setStyleSheet(f"""
                    QLineEdit {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 14px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)
                self._configure_possession_line_edit(home_time, "home")
                home_value = home_time

            else:
                # For non-controlled stats (not time), default to 0; possession percent handled separately
                default_home_text = "0"
                home_value = ModernLabel(
                    default_home_text, "body", stats_panel, font_size=16
                )
                home_value.setGeometry(55, y_pos, 90, 30)
                home_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                home_value.setStyleSheet(f"""
                    QLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 16px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)

            # Create the center column label unless this is the special possession-time spacer row
            stat_label = None
            if not (is_possession and label_text == ""):
                stat_label = ModernLabel(label_text, "body", stats_panel, font_size=14)
                # Use narrower width for stat labels (reduced from full stat_col_width)
                # Adjust stat_label_width to change the width of stat labels (Kickoff, Goals, Shots, etc.)
                stat_label_width = max(
                    145, stat_col_width - 40
                )  # Change 120 to adjust max width, or change -40 paddin
                # Adjust stat_label_x to move stat labels left/right: add offset to shift, e.g., +10 or -10
                stat_label_x = (
                    stat_x + (stat_col_width - stat_label_width) // 2
                )  # Center the narrower label
                stat_label.setGeometry(stat_label_x, y_pos, stat_label_width, 30)
                stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if stat_label is not None:
                if "Yellow" in label_text:
                    stat_label.setStyleSheet(f"""
                        QLabel {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #fbbf24, stop:1 #f59e0b);
                            color: {CONFIG["colors"]["background"]};
                            font-size: 14px;
                            font-weight: 600;
                            border: 1px solid {CONFIG["colors"]["border"]};
                            border-radius: 4px;
                        }}
                    """)
                elif "Red" in label_text:
                    stat_label.setStyleSheet(f"""
                        QLabel {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {CONFIG["colors"]["button_danger"]}, stop:1 #b91c1c);
                            color: {CONFIG["colors"]["background"]};
                            font-size: 14px;
                            font-weight: 600;
                            border: 1px solid {CONFIG["colors"]["border"]};
                            border-radius: 4px;
                        }}
                    """)
                else:
                    stat_label.setStyleSheet(f"""
                        QLabel {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                            color: {CONFIG["colors"]["text"]};
                            font-size: 14px;
                            font-weight: 600;
                            border: 1px solid {CONFIG["colors"]["border"]};
                            border-radius: 4px;
                        }}
                    """)

            if has_controls:
                away_dec_x = away_header_x - 12
                away_value_x = away_dec_x + 35
                away_inc_x = away_dec_x + 130
                away_dec = ModernButton("◄", "primary", stats_panel, font_size=16)
                away_dec.setGeometry(away_dec_x, y_pos, 30, 30)
                animator_away_dec = FontSizeAnimator(away_dec, 16)
                self.button_animators[away_dec] = animator_away_dec
                away_dec.clicked.connect(
                    lambda checked, key=stat_key, team="away": self.safe_decrease_stat(
                        key, team
                    )
                )
                away_dec.clicked.connect(lambda: self.animate_button_click(away_dec))

                away_value = ModernLabel("0", "body", stats_panel, font_size=16)
                away_value.setGeometry(away_value_x, y_pos, 90, 30)
                away_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                away_value.setStyleSheet(f"""
                    QLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 16px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)

                away_inc = ModernButton("►", "primary", stats_panel, font_size=16)
                away_inc.setGeometry(away_inc_x, y_pos, 30, 30)
                animator_away_inc = FontSizeAnimator(away_inc, 16)
                self.button_animators[away_inc] = animator_away_inc
                away_inc.clicked.connect(
                    lambda checked, key=stat_key, team="away": self.increase_stat(
                        key, team
                    )
                )
                away_inc.clicked.connect(lambda: self.animate_button_click(away_inc))

            elif is_possession:
                from PySide6.QtWidgets import QLineEdit

                away_value_x = away_header_x + 17
                away_time = QLineEdit("00:00", stats_panel)
                away_time.setGeometry(away_value_x, y_pos, 100, 30)
                away_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
                try:
                    away_time.setInputMask("00:00")
                except Exception:
                    pass
                away_time.setStyleSheet(f"""
                    QLineEdit {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 14px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)
                self._configure_possession_line_edit(away_time, "away")
                away_value = away_time

            else:
                # For non-controlled stats (not time), default to 0; possession percent handled separately
                default_away_text = "0"
                away_value_x = away_header_x + 22
                away_value = ModernLabel(
                    default_away_text, "body", stats_panel, font_size=16
                )
                away_value.setGeometry(away_value_x, y_pos, 90, 30)
                away_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                away_value.setStyleSheet(f"""
                    QLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        color: #b6b6b8;
                        font-size: 16px;
                        font-weight: 600;
                        border: 1px solid {CONFIG["colors"]["border"]};
                        border-radius: 4px;
                    }}
                """)

            # Store value labels and, if present, control buttons
            entry = {"home_value": home_value, "away_value": away_value}
            if has_controls:
                entry.update(
                    {
                        "home_dec": home_dec,
                        "home_inc": home_inc,
                        "away_dec": away_dec,
                        "away_inc": away_inc,
                    }
                )
            self.stats_widgets[stat_key] = entry

    # Add all missing utility methods for complete functionality
    def update_time_type(self):
        """Update the time type based on radio button selection."""
        if self.radio_current_time.isChecked():
            self.time_type = "CT"
        elif self.radio_half_time.isChecked():
            self.time_type = "HT"
        elif self.radio_full_time.isChecked():
            self.time_type = "FT"
        elif self.radio_extra_time.isChecked():
            self.time_type = "ET"

    def toggle_extra_time_label(self, state):
        """Toggle visibility of the extra time label."""
        self.extra_time_value_label.setVisible(state == Qt.CheckState.Checked.value)

    def apply_extra_time(self):
        """Apply extra time settings."""
        self.extra_time_enabled = self.extra_time_check.isChecked()
        self.extra_time_minutes = self.extra_time_spin.value()
        self.extra_time_value_label.setText(f"+{self.extra_time_minutes}")

    def reset_timer(self):
        """Reset only Extra Time settings (do not touch main timer)."""
        # Leave self.seconds, running state, and MIN/SEC inputs unchanged
        self.extra_time_enabled = False
        self.extra_time_minutes = 0
        if hasattr(self, "extra_time_spin"):
            self.extra_time_spin.setValue(0)
        if hasattr(self, "extra_time_check"):
            self.extra_time_check.setChecked(False)
        if hasattr(self, "extra_time_value_label"):
            self.extra_time_value_label.setText("+0")
            self.extra_time_value_label.setVisible(False)

    def increase_stat(self, stat_key, team):
        """Increase a statistic for the specified team."""
        key = f"{team}_{stat_key}"
        if key in self.stats_data:
            try:
                print(
                    f"DEBUG increase_stat: team={team}, stat={stat_key}, before={self.stats_data[key]}"
                )
            except Exception:
                pass
            self.stats_data[key] += 1
            self.update_stat_display(stat_key, team)
            try:
                print(f"Increased {team} {stat_key} to {self.stats_data[key]}")
            except Exception:
                pass
            # Keep Shots in sync when Shots on Target changes
            if stat_key == "shots_on_target":
                shots_key = f"{team}_shots"
                if shots_key in self.stats_data:
                    self.stats_data[shots_key] += 1
                    self.update_stat_display("shots", team)
            # Ensure Shots on Target increases with Goals
            if stat_key == "goals":
                self.increase_stat("shots_on_target", team)
            # Enforce invariants (SOT >= Goals, Shots >= SOT)
            self._enforce_stats_invariants(team)
            if stat_key == "goals":
                # Also update the main goal display
                if team == "home":
                    self.home_goals = self.stats_data[key]
                    self.home_goal_label.setText(str(self.home_goals))
                    current_time = self.timer_label.text()
                    if hasattr(self, "home_scorer_panel"):
                        self.home_scorer_panel.update_goals(
                            self.home_goals, current_time
                        )
                else:
                    self.away_goals = self.stats_data[key]
                    self.away_goal_label.setText(str(self.away_goals))
                    current_time = self.timer_label.text()
                    if hasattr(self, "away_scorer_panel"):
                        self.away_scorer_panel.update_goals(
                            self.away_goals, current_time
                        )

    def decrease_stat(self, stat_key, team):
        """Decrease a statistic for the specified team."""
        key = f"{team}_{stat_key}"
        if key in self.stats_data and self.stats_data[key] > 0:
            try:
                print(
                    f"DEBUG decrease_stat(entry): team={team}, stat={stat_key}, current={self.stats_data[key]}"
                )
            except Exception:
                pass
            try:
                print(
                    f"DEBUG decrease_stat: team={team}, stat={stat_key}, before={self.stats_data[key]}"
                )
            except Exception:
                pass
            # Prevent Shots on Target from going below Goals
            if stat_key == "shots_on_target":
                # Use stats_data goals, but also fall back to the visible goal label to avoid desync
                goals_key = f"{team}_goals"
                goals_val_data = self.stats_data.get(goals_key, 0)
                try:
                    label_val = (
                        int(self.home_goal_label.text())
                        if team == "home"
                        else int(self.away_goal_label.text())
                    )
                except Exception:
                    label_val = 0
                goals_val = max(goals_val_data, label_val)
                try:
                    print(
                        f"DEBUG decrease_stat: team={team}, stat=shots_on_target, current={self.stats_data[key]}, goals={goals_val}"
                    )
                except Exception:
                    pass
                if self.stats_data[key] - 1 < goals_val:
                    # Do not allow decrement below goals
                    try:
                        print(
                            "DEBUG decrease_stat: block decrement SOT because it would go below goals"
                        )
                    except Exception:
                        pass
                    return
            # Prevent Shots from going below Shots on Target
            if stat_key == "shots":
                sot_val = self.stats_data.get(f"{team}_shots_on_target", 0)
                try:
                    print(
                        f"DEBUG decrease_stat: team={team}, stat=shots, current={self.stats_data[key]}, sot={sot_val}"
                    )
                except Exception:
                    pass
                if self.stats_data[key] - 1 < sot_val:
                    try:
                        print(
                            "DEBUG decrease_stat: block decrement Shots because it would go below SOT"
                        )
                    except Exception:
                        pass
                    return
            self.stats_data[key] -= 1
            self.update_stat_display(stat_key, team)
            try:
                print(f"Decreased {team} {stat_key} to {self.stats_data[key]}")
            except Exception:
                pass
            # Keep Shots in sync when Shots on Target changes
            if stat_key == "shots_on_target":
                shots_key = f"{team}_shots"
                if shots_key in self.stats_data and self.stats_data[shots_key] > 0:
                    self.stats_data[shots_key] -= 1
                    self.update_stat_display("shots", team)
                # Post-decrement safety: ensure SOT not below Goals
                try:
                    goals_key = f"{team}_goals"
                    goals_val_data = self.stats_data.get(goals_key, 0)
                    label_val = (
                        int(self.home_goal_label.text())
                        if team == "home"
                        else int(self.away_goal_label.text())
                    )
                except Exception:
                    label_val = 0
                goals_val = max(goals_val_data, label_val)
                if self.stats_data[key] < goals_val:
                    try:
                        print(
                            f"DEBUG post-fix SOT: bumping {team} SOT {self.stats_data[key]} -> {goals_val} (goals)"
                        )
                    except Exception:
                        pass
                    self.stats_data[key] = goals_val
                    self.update_stat_display(stat_key, team)
            # Enforce invariants (SOT >= Goals, Shots >= SOT)
            self._enforce_stats_invariants(team)
            if stat_key == "goals":
                # Also update the main goal display
                if team == "home":
                    self.home_goals = self.stats_data[key]
                    self.home_goal_label.setText(str(self.home_goals))
                    current_time = self.timer_label.text()
                    if hasattr(self, "home_scorer_panel"):
                        self.home_scorer_panel.update_goals(
                            self.home_goals, current_time
                        )
                else:
                    self.away_goals = self.stats_data[key]
                    self.away_goal_label.setText(str(self.away_goals))
                    current_time = self.timer_label.text()
                    if hasattr(self, "away_scorer_panel"):
                        self.away_scorer_panel.update_goals(
                            self.away_goals, current_time
                        )
                # After decreasing goals, reduce shots on target by 1 only if above new goals
                sot_key = f"{team}_shots_on_target"
                if self.stats_data.get(sot_key, 0) > self.stats_data[key]:
                    self.decrease_stat("shots_on_target", team)

    def safe_decrease_stat(self, stat_key, team):
        """Wrapper around decrease_stat with an extra pre-check for SOT>=Goals."""
        if stat_key == "shots_on_target":
            try:
                goals_key = f"{team}_goals"
                goals_val_data = self.stats_data.get(goals_key, 0)
                label_val = (
                    int(self.home_goal_label.text())
                    if team == "home"
                    else int(self.away_goal_label.text())
                )
            except Exception:
                label_val = 0
            min_allowed = max(goals_val_data, label_val)
            current = self.stats_data.get(f"{team}_shots_on_target", 0)
            if current - 1 < min_allowed:
                try:
                    print(
                        f"DEBUG safe_decrease_stat: blocked {team} SOT decrement {current}-> {current - 1} < goals {min_allowed}"
                    )
                except Exception:
                    pass
                return
        self.decrease_stat(stat_key, team)

    def update_stat_display(self, stat_key, team):
        """Update the display of a statistic."""
        if stat_key in self.stats_widgets:
            key = f"{team}_{stat_key}"
            value = self.stats_data.get(key, 0)
            try:
                print(
                    f"DEBUG update_stat_display: team={team}, stat={stat_key}, value={value}"
                )
            except Exception:
                pass
            widget = self.stats_widgets[stat_key][f"{team}_value"]
            if stat_key == "possession_time":
                mins, secs = divmod(value, 60)
                widget.setText(f"{mins:02d}:{secs:02d}")
            else:
                widget.setText(str(value))
            # Safety net: never allow SOT < Goals even if another path changed it
            if stat_key == "shots_on_target":
                try:
                    goals_key = f"{team}_goals"
                    goals_val_data = self.stats_data.get(goals_key, 0)
                    label_val = (
                        int(self.home_goal_label.text())
                        if team == "home"
                        else int(self.away_goal_label.text())
                    )
                except Exception:
                    label_val = 0
                min_allowed = max(goals_val_data, label_val)
                if value < min_allowed:
                    try:
                        print(
                            f"DEBUG update_stat_display fix: raising {team} SOT {value} -> {min_allowed}"
                        )
                    except Exception:
                        pass
                    self.stats_data[key] = min_allowed
                    self.stats_widgets[stat_key][f"{team}_value"].setText(
                        str(min_allowed)
                    )
            # Update possession percentage if possession time changes
            if stat_key == "possession_time":
                self.update_possession_percentages()
        # Enforce invariants whenever any stat display is updated (catch-all)
        if team in ("home", "away"):
            self._enforce_stats_invariants(team)

    def _enforce_stats_invariants(self, team: str):
        """Ensure shots on target >= goals, and shots >= shots on target for a team."""
        goals_key = f"{team}_goals"
        sot_key = f"{team}_shots_on_target"
        shots_key = f"{team}_shots"
        # Use the higher of stored goals and the visible label to avoid desync edge cases
        goals_val_data = self.stats_data.get(goals_key, 0)
        try:
            label_goals = (
                int(self.home_goal_label.text())
                if team == "home"
                else int(self.away_goal_label.text())
            )
        except Exception:
            label_goals = 0
        goals_val = max(goals_val_data, label_goals)
        sot_val = self.stats_data.get(sot_key, 0)
        shots_val = self.stats_data.get(shots_key, 0)
        try:
            print(
                f"DEBUG invariants(before): team={team}, goals={goals_val}, sot={sot_val}, shots={shots_val}"
            )
        except Exception:
            pass

        # Shots on target must be at least goals
        if sot_val < goals_val:
            self.stats_data[sot_key] = goals_val
            self.update_stat_display("shots_on_target", team)
            try:
                print(f"DEBUG invariants: corrected sot -> {goals_val}")
            except Exception:
                pass

        # Shots must be at least shots on target
        if shots_val < self.stats_data.get(sot_key, goals_val):
            self.stats_data[shots_key] = self.stats_data.get(sot_key, goals_val)
            self.update_stat_display("shots", team)
            try:
                print(
                    f"DEBUG invariants: corrected shots -> {self.stats_data.get(shots_key, 0)}"
                )
            except Exception:
                pass

        # Do not lock any buttons; keep them enabled at all times
        # Invariants are enforced via value guards in increase/decrease handlers

    def update_possession_percentages(self):
        """Update possession percentages based on possession time."""
        home_time = self.stats_data["home_possession_time"]
        away_time = self.stats_data["away_possession_time"]
        total_time = home_time + away_time
        if total_time > 0:
            home_pct = round((home_time / total_time) * 100)
            away_pct = round((away_time / total_time) * 100)
        else:
            home_pct = away_pct = 50
        # Update possession percentage displays
        if "possession" in self.stats_widgets:
            self.stats_widgets["possession"]["home_value"].setText(str(home_pct))
            self.stats_widgets["possession"]["away_value"].setText(str(away_pct))

    def deploy_stat(self, stat_key):
        """Deploy/broadcast a statistic."""
        print(f"Deploying {stat_key} statistics")
        # Deploy all statistics at once
        for key, widgets in self.stats_widgets.items():
            print(
                f"  - {key}: Home={widgets['home_value'].text()}, Away={widgets['away_value'].text()}"
            )

    def deploy_all_stats(self):
        """Deploy all match statistics at once."""
        print("=== DEPLOYING ALL MATCH STATISTICS ===")
        for key, widgets in self.stats_widgets.items():
            print(
                f"  - {key}: Home={widgets['home_value'].text()}, Away={widgets['away_value'].text()}"
            )
        print("=== ALL STATISTICS DEPLOYED ===")

        # Visual feedback for deployment
        original_style = self.stats_deploy_button.styleSheet()
        self.stats_deploy_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8);
                color: white;
                border: 2px solid #1e40af;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
            }}
        """)

        # Reset button style after brief delay
        QTimer.singleShot(
            1000, lambda: self.stats_deploy_button.setStyleSheet(original_style)
        )

    def reset_deploy_button_style(self, button, original_style):
        """Reset deploy button style after deployment."""
        button.style_type = original_style
        button.apply_style()

    def reset_match(self):
        """Reset Play On tab to the state right after match creation."""
        try:
            # Stop timers and reset time
            if hasattr(self, "timer") and self.timer is not None:
                try:
                    self.timer.stop()
                except Exception:
                    pass
            self.timer_running = False
            self.seconds = 0
            if hasattr(self, "timer_label"):
                self.timer_label.setText("00:00")
            # Extra time
            self.extra_time_enabled = False
            self.extra_time_minutes = 0
            if hasattr(self, "extra_time_spin"):
                self.extra_time_spin.setValue(0)
            if hasattr(self, "extra_time_check"):
                self.extra_time_check.setChecked(False)
            if hasattr(self, "extra_time_value_label"):
                self.extra_time_value_label.setText("+0")
                self.extra_time_value_label.setVisible(False)

            # Reset goals on main scoreboard (labels remain static names)
            self.home_goals = 0
            self.away_goals = 0
            if hasattr(self, "home_goal_label"):
                self.home_goal_label.setText("0")
            if hasattr(self, "away_goal_label"):
                self.away_goal_label.setText("0")

            # Reset possession state and visuals
            self.home_ball_control_time = 0
            self.away_ball_control_time = 0
            self.current_possession = None
            try:
                self.update_team_panel_borders()
            except Exception:
                pass
            # Reset possession widgets if exist
            if "possession_time" in getattr(self, "stats_widgets", {}):
                hv = self.stats_widgets["possession_time"]["home_value"]
                av = self.stats_widgets["possession_time"]["away_value"]
                hv.setText("00:00")
                av.setText("00:00")
                # Restore default styles for QLineEdit widgets (possession time fields are now editable)
                try:
                    hv.setStyleSheet(f"""
                        QLineEdit {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                            color: {CONFIG["colors"]["text"]};
                            font-size: 14px;
                            font-weight: 600;
                            border: 1px solid {CONFIG["colors"]["border"]};
                            border-radius: 4px;
                        }}
                    """)
                    av.setStyleSheet(f"""
                        QLineEdit {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                            color: {CONFIG["colors"]["text"]};
                            font-size: 14px;
                            font-weight: 600;
                            border: 1px solid {CONFIG["colors"]["border"]};
                            border-radius: 4px;
                        }}
                    """)
                except Exception:
                    pass
            if "possession" in getattr(self, "stats_widgets", {}):
                self.stats_widgets["possession"]["home_value"].setText("50")
                self.stats_widgets["possession"]["away_value"].setText("50")
            if hasattr(self, "possession_toggle_btn"):
                self.possession_toggle_btn.setText("Kickoff")
                self._apply_possession_button_style("neutral")

            # Reset statistics data and displays
            for key in list(self.stats_data.keys()):
                self.stats_data[key] = 0
            # Keep goals labels already set; update stats widgets to zero
            for stat_key, widgets in getattr(self, "stats_widgets", {}).items():
                if stat_key == "possession_time":
                    continue
                widgets["home_value"].setText("0")
                widgets["away_value"].setText("0")

            # Reset scorer-related tables by clearing any QTableWidget children
            try:
                from PySide6.QtWidgets import QTableWidget

                if hasattr(self, "home_scorer_panel"):
                    for t in self.home_scorer_panel.findChildren(QTableWidget):
                        t.setRowCount(0)
                if hasattr(self, "away_scorer_panel"):
                    for t in self.away_scorer_panel.findChildren(QTableWidget):
                        t.setRowCount(0)
            except Exception:
                pass

            # Reset header highlights
            try:
                if hasattr(self, "stats_home_header_label") and hasattr(
                    self, "stats_header_default_style"
                ):
                    self.stats_home_header_label.setStyleSheet(
                        self.stats_header_default_style
                    )
                if hasattr(self, "stats_away_header_label") and hasattr(
                    self, "stats_header_default_style"
                ):
                    self.stats_away_header_label.setStyleSheet(
                        self.stats_header_default_style
                    )
            except Exception:
                pass
        except Exception as e:
            print(f"Error in reset_match: {e}")

    def _recompute_team_cards_and_fouls(self, team: str):
        """Scan the team's cards tables and set yellow/red and fouls accordingly."""
        try:
            from PySide6.QtWidgets import QTableWidget

            panel = self.home_scorer_panel if team == "home" else self.away_scorer_panel
            yellow = 0
            red = 0
            scanned = False
            if panel is not None:
                for tbl in panel.findChildren(QTableWidget):
                    scanned = True
                    rows = tbl.rowCount()
                    for r in range(rows):
                        # Skip hidden rows (treated as cleared)
                        try:
                            if tbl.isRowHidden(r):
                                continue
                        except Exception:
                            pass
                        # Column indices: Yellow=3, Red=4 per current layout
                        y_w = tbl.cellWidget(r, 3)
                        if y_w is not None:
                            cb = y_w.findChild(QCheckBox)
                            if cb and cb.isChecked():
                                yellow += 1
                        r_w = tbl.cellWidget(r, 4)
                        if r_w is not None:
                            cb = r_w.findChild(QCheckBox)
                            if cb and cb.isChecked():
                                red += 1
            # If no tables found via panel, try alternate attributes
            if not scanned:
                alt_tbl = getattr(
                    self,
                    "home_card_table" if team == "home" else "away_card_table",
                    None,
                )
                if isinstance(alt_tbl, QTableWidget):
                    rows = alt_tbl.rowCount()
                    for r in range(rows):
                        # Skip hidden rows
                        try:
                            if alt_tbl.isRowHidden(r):
                                continue
                        except Exception:
                            pass
                        y_w = alt_tbl.cellWidget(r, 3)
                        if y_w is not None:
                            cb = y_w.findChild(QCheckBox)
                            if cb and cb.isChecked():
                                yellow += 1
                        r_w = alt_tbl.cellWidget(r, 4)
                        if r_w is not None:
                            cb = r_w.findChild(QCheckBox)
                            if cb and cb.isChecked():
                                red += 1
            # Apply to stats and update
            y_key = f"{team}_yellow_cards"
            r_key = f"{team}_red_cards"
            f_key = f"{team}_fouls"
            prev_total_cards = self.stats_data.get(y_key, 0) + self.stats_data.get(
                r_key, 0
            )
            self.stats_data[y_key] = yellow
            self.stats_data[r_key] = red
            delta_cards = (yellow + red) - prev_total_cards
            self.stats_data[f_key] = max(0, self.stats_data.get(f_key, 0) + delta_cards)
            self.update_stat_display("yellow_cards", team)
            self.update_stat_display("red_cards", team)
            self.update_stat_display("fouls", team)
        except Exception as e:
            try:
                print(f"Error in _recompute_team_cards_and_fouls: {e}")
            except Exception:
                pass

    # Possession tracking methods (from Play_On.py)
    def _apply_possession_button_style(self, state: str):
        """Apply consistent styling to the possession toggle button."""
        try:
            button = getattr(self, "possession_toggle_btn", None)
            if not button:
                return
            neutral_style = """
                QPushButton {
                    font-weight: bold;
                    font-size: 16px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6b7280, stop:1 #4b5563);
                    color: #ffffff;
                    border: 2px solid #374151;
                    border-radius: 6px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #71717a, stop:1 #52525b);
                    border: 2px solid #52525b;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3b82f6, stop:1 #1d4ed8);
                    border: 2px solid #1d4ed8;
                }
            """
            active_template = """
                QPushButton {{
                    font-weight: bold;
                    font-size: 16px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {button_primary}, stop:1 {button_primary});
                    color: {text_color};
                    border: 2px solid {border_color};
                    border-radius: 6px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {button_primary}, stop:1 {accent});
                    border: 2px solid {accent};
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {accent}, stop:1 {button_primary});
                    border: 2px solid {accent};
                }}
            """
            active_style = active_template.format(
                button_primary=CONFIG["colors"]["button_primary"],
                text_color=CONFIG["colors"]["text"],
                border_color=CONFIG["colors"]["border"],
                accent=CONFIG["colors"]["accent"],
            )
            style = neutral_style if state == "neutral" else active_style
            if hasattr(button, "set_custom_stylesheet"):
                button.set_custom_stylesheet(style)
            else:
                button.setStyleSheet(style)
        except Exception:
            pass

    def toggle_possession(self):
        """Toggle possession between home and away teams (styled like reference)."""
        try:
            # Get short names from team data with fallback
            home_short = "Home Team"
            away_short = "Away Team"

            if hasattr(self, "home_team_data") and self.home_team_data:
                home_short = (
                    self.home_team_data.get("short_name")
                    or self.home_team_data.get("name")
                    or "Home Team"
                )

            if hasattr(self, "away_team_data") and self.away_team_data:
                away_short = (
                    self.away_team_data.get("short_name")
                    or self.away_team_data.get("name")
                    or "Away Team"
                )

            # Toggle logic: First click immediately toggles (None -> home -> away), then cycles
            # This ensures the first click performs a toggle action instead of just setting initial state
            if self.current_possession is None:
                # First click: immediately toggle to away (so it's a toggle, not just a set)
                self.current_possession = "away"
                if hasattr(self, "possession_toggle_btn"):
                    self.possession_toggle_btn.setText(away_short)
                    self._apply_possession_button_style("active")
            elif self.current_possession == "home":
                # Toggle to away
                self.current_possession = "away"
                if hasattr(self, "possession_toggle_btn"):
                    self.possession_toggle_btn.setText(away_short)
                    self._apply_possession_button_style("active")
            elif self.current_possession == "away":
                # Toggle back to home
                self.current_possession = "home"
                if hasattr(self, "possession_toggle_btn"):
                    self.possession_toggle_btn.setText(home_short)
                    self._apply_possession_button_style("active")
            else:
                # Fallback: reset to away if state is invalid
                self.current_possession = "away"
                if hasattr(self, "possession_toggle_btn"):
                    self.possession_toggle_btn.setText(away_short)
                    self._apply_possession_button_style("active")

            # Always clear the suppress flag when toggling possession (after first click or any toggle)
            # This ensures highlighting works for all clicks
            self._suppress_possession_highlight_once = False

            if hasattr(self, "btn_start") and not self.btn_start.isEnabled():
                self.btn_start.setEnabled(True)

            # Update possession times and highlights
            self.update_possession_times()

            # Explicitly update highlights to ensure they're applied
            try:
                # Update header label colors
                if (
                    hasattr(self, "stats_home_header_label")
                    and hasattr(self, "stats_away_header_label")
                    and hasattr(self, "stats_header_active_style")
                    and hasattr(self, "stats_header_default_style")
                ):
                    if self.current_possession == "home":
                        self.stats_home_header_label.setStyleSheet(
                            self.stats_header_active_style
                        )
                        self.stats_away_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
                    elif self.current_possession == "away":
                        self.stats_home_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
                        self.stats_away_header_label.setStyleSheet(
                            self.stats_header_active_style
                        )

                # Update team panel borders
                self.update_team_panel_borders()
            except Exception as e:
                try:
                    print(f"Error updating highlights in toggle_possession: {e}")
                except Exception:
                    pass
        except Exception as e:
            print(f"Error in toggle_possession: {str(e)}")

    def set_possession(self, side: str):
        """
        Single-way setter: sets possession to 'home' or 'away' by clicking the same
        toggle button only when a change is needed.
        """
        try:
            side = (side or "").lower()
            if side not in ("home", "away"):
                return
            if getattr(self, "current_possession", None) == side:
                return  # already on requested side
            if hasattr(self, "possession_toggle_btn") and self.possession_toggle_btn:
                self.possession_toggle_btn.click()
                try:
                    QTimer.singleShot(0, self.update_team_panel_borders)
                except Exception:
                    pass
        except Exception as e:
            try:
                print(f"Error in set_possession('{side}'): {e}")
            except Exception:
                pass

    def update_possession_button(self, team_name):
        """Update the possession button styling and text"""
        # Find the possession button in stats panel (if it exists)
        # This will be connected when the stats panel is fully implemented
        pass

    def _rebalance_possession_times(self):
        """Ensure combined possession time never exceeds elapsed match time."""
        try:
            elapsed = max(int(getattr(self, "seconds", 0)), 0)
            home_time = max(0, int(self.home_ball_control_time))
            away_time = max(0, int(self.away_ball_control_time))
            total = home_time + away_time
            if elapsed <= 0:
                self.home_ball_control_time = 0
                self.away_ball_control_time = 0
                return
            if total <= elapsed:
                self.home_ball_control_time = home_time
                self.away_ball_control_time = away_time
                return
            surplus = total - elapsed

            def trim(team: str):
                nonlocal surplus, home_time, away_time
                if surplus <= 0:
                    return
                if team == "home":
                    reduction = min(home_time, surplus)
                    home_time -= reduction
                else:
                    reduction = min(away_time, surplus)
                    away_time -= reduction
                surplus -= reduction

            possession = getattr(self, "current_possession", None)
            if possession == "home":
                trim("away")
                trim("home")
            elif possession == "away":
                trim("home")
                trim("away")
            else:
                if home_time >= away_time:
                    trim("home")
                    trim("away")
                else:
                    trim("away")
                    trim("home")
            if surplus > 0:
                trim("home")
                trim("away")

            self.home_ball_control_time = max(0, home_time)
            self.away_ball_control_time = max(0, away_time)
        except Exception:
            pass

    def update_possession_times(self):
        """Update Ball Control times, Possession percentages, and visual indicators."""
        try:
            home_widget = None
            away_widget = None
            if (
                hasattr(self, "stats_widgets")
                and "possession_time" in self.stats_widgets
            ):
                home_widget = self.stats_widgets["possession_time"]["home_value"]
                away_widget = self.stats_widgets["possession_time"]["away_value"]

            if self.timer_running and self.current_possession:
                if self.current_possession == "home":
                    self.home_ball_control_time += 1
                else:
                    self.away_ball_control_time += 1

                self._rebalance_possession_times()

            # Update possession data and display (whether timer is running or not)
            self.stats_data["home_possession_time"] = self.home_ball_control_time
            self.stats_data["away_possession_time"] = self.away_ball_control_time

            total_time = self.home_ball_control_time + self.away_ball_control_time
            if total_time > 0:
                home_possession = round(
                    (self.home_ball_control_time / total_time) * 100
                )
                away_possession = round(
                    (self.away_ball_control_time / total_time) * 100
                )
            else:
                # At the beginning, show 0% for both teams
                home_possession = 0
                away_possession = 0

            if home_widget and away_widget:
                home_mins, home_secs = divmod(self.home_ball_control_time, 60)
                away_mins, away_secs = divmod(self.away_ball_control_time, 60)
                home_widget.setText(f"{home_mins:02d}:{home_secs:02d}")
                away_widget.setText(f"{away_mins:02d}:{away_secs:02d}")

            if hasattr(self, "stats_widgets") and "possession" in self.stats_widgets:
                home_pct_widget = self.stats_widgets["possession"]["home_value"]
                away_pct_widget = self.stats_widgets["possession"]["away_value"]
                home_pct_widget.setText(str(home_possession))
                away_pct_widget.setText(str(away_possession))

            highlight_allowed = not getattr(
                self, "_suppress_possession_highlight_once", False
            )
            try:
                if hasattr(self, "stats_home_header_label") and hasattr(
                    self, "stats_away_header_label"
                ):
                    if highlight_allowed and self.current_possession == "home":
                        self.stats_home_header_label.setStyleSheet(
                            self.stats_header_active_style
                        )
                        self.stats_away_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
                    elif highlight_allowed and self.current_possession == "away":
                        self.stats_home_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
                        self.stats_away_header_label.setStyleSheet(
                            self.stats_header_active_style
                        )
                    elif not highlight_allowed or self.current_possession is None:
                        # Default state: no highlight
                        self.stats_home_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
                        self.stats_away_header_label.setStyleSheet(
                            self.stats_header_default_style
                        )
            except Exception as e:
                # Debug: print error to see what's happening
                try:
                    print(f"Error updating header labels: {e}")
                except Exception:
                    pass

            try:
                self.update_team_panel_borders()
            except Exception:
                pass

        except Exception as e:
            print(f"Error in update_possession_times: {str(e)}")

    def update_team_panel_borders(self):
        """Highlight team panel border red for the team currently in possession."""
        try:
            border_highlight = CONFIG["colors"]["button_danger"]
            border_default = CONFIG["colors"]["border"]
            highlight_allowed = not getattr(
                self, "_suppress_possession_highlight_once", False
            )

            def panel_style(obj_name: str, border_color: str) -> str:
                return f"""
                    #{obj_name} {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {CONFIG["colors"]["card"]}, stop:1 {CONFIG["colors"]["panel"]});
                        border: 2px solid {border_color};
                        border-radius: 10px;
                    }}
                """

            if hasattr(self, "home_team_panel"):
                home_border = (
                    border_highlight
                    if (highlight_allowed and self.current_possession == "home")
                    else border_default
                )
                self.home_team_panel.setStyleSheet(
                    panel_style(self.home_team_panel.objectName(), home_border)
                )
            if hasattr(self, "away_team_panel"):
                away_border = (
                    border_highlight
                    if (highlight_allowed and self.current_possession == "away")
                    else border_default
                )
                self.away_team_panel.setStyleSheet(
                    panel_style(self.away_team_panel.objectName(), away_border)
                )
        except Exception as e:
            try:
                print(f"Error in update_team_panel_borders: {e}")
            except Exception:
                pass

    def update_scorer_time_for_goal(self, team_type, current_time):
        """Update the time for the first empty row when a goal is scored"""
        try:
            if team_type == "home" and hasattr(self, "home_scorer_panel"):
                self.home_scorer_panel.update_scorer_time(current_time)
            elif team_type == "away" and hasattr(self, "away_scorer_panel"):
                self.away_scorer_panel.update_scorer_time(current_time)
        except Exception as e:
            print(f"Error in update_scorer_time_for_goal: {str(e)}")

    def animate_button_click(self, button):
        """Animate button click with font size change"""
        try:
            from PySide6.QtCore import QEasingCurve, QPropertyAnimation

            if button in self.button_animators:
                animator = self.button_animators[button]

                # Create animation for font size
                animation = QPropertyAnimation(animator, b"fontSize")
                animation.setDuration(150)  # 150ms animation
                animation.setStartValue(animator.original_size)
                animation.setEndValue(animator.original_size + 5)  # Increase by 5
                animation.setEasingCurve(QEasingCurve.OutQuad)

                # Return to original size
                def return_to_original():
                    return_animation = QPropertyAnimation(animator, b"fontSize")
                    return_animation.setDuration(150)
                    return_animation.setStartValue(animator.original_size + 5)
                    return_animation.setEndValue(animator.original_size)
                    return_animation.setEasingCurve(QEasingCurve.InQuad)
                    return_animation.start()

                animation.finished.connect(return_to_original)
                animation.start()

        except Exception as e:
            print(f"Error in animate_button_click: {str(e)}")

    def increase_stat(self, stat_key, team):
        """Increase a statistic for the specified team"""
        try:
            data_key = f"{team}_{stat_key}"
            if data_key in self.stats_data:
                self.stats_data[data_key] += 1

                # Update the display widget
                if hasattr(self, "stats_widgets") and stat_key in self.stats_widgets:
                    widget = self.stats_widgets[stat_key][f"{team}_value"]
                    widget.setText(str(self.stats_data[data_key]))

                # When shots_on_target increases, also increase shots
                if stat_key == "shots_on_target":
                    shots_key = f"{team}_shots"
                    if shots_key in self.stats_data:
                        self.stats_data[shots_key] += 1
                        if (
                            hasattr(self, "stats_widgets")
                            and "shots" in self.stats_widgets
                        ):
                            shots_widget = self.stats_widgets["shots"][f"{team}_value"]
                            shots_widget.setText(str(self.stats_data[shots_key]))

                print(f"Increased {team} {stat_key} to {self.stats_data[data_key]}")

        except Exception as e:
            print(f"Error in increase_stat: {e}")

    def decrease_stat(self, stat_key, team):
        """Decrease a statistic for the specified team"""
        try:
            data_key = f"{team}_{stat_key}"
            if data_key in self.stats_data and self.stats_data[data_key] > 0:
                # Prevent shots from going below shots_on_target
                if stat_key == "shots":
                    sot = int(self.stats_data.get(f"{team}_shots_on_target", 0))
                    if self.stats_data[data_key] <= sot:
                        return
                self.stats_data[data_key] -= 1

                # Update the display widget
                if hasattr(self, "stats_widgets") and stat_key in self.stats_widgets:
                    widget = self.stats_widgets[stat_key][f"{team}_value"]
                    widget.setText(str(self.stats_data[data_key]))

                # When shots_on_target decreases, also decrease shots
                if stat_key == "shots_on_target":
                    shots_key = f"{team}_shots"
                    if shots_key in self.stats_data and self.stats_data[shots_key] > 0:
                        self.stats_data[shots_key] -= 1
                        if (
                            hasattr(self, "stats_widgets")
                            and "shots" in self.stats_widgets
                        ):
                            shots_widget = self.stats_widgets["shots"][f"{team}_value"]
                            shots_widget.setText(str(self.stats_data[shots_key]))

                print(f"Decreased {team} {stat_key} to {self.stats_data[data_key]}")

        except Exception as e:
            print(f"Error in decrease_stat: {e}")

    def update_stats_for_card(self, team_type, card_type):
        """Update statistics when a card checkbox changes (recompute from table)."""
        try:
            # Instead of incrementing blindly, always recompute from the visible card table
            self.update_card_stats(team_type)
            print(f"Updated stats from table for {team_type} after {card_type} change")
        except Exception as e:
            print(f"Error in update_stats_for_card: {e}")

    def on_yellow_card_changed(self, state, team_type, row, table):
        """Handle yellow card checkbox state change"""
        try:
            from PySide6.QtCore import Qt

            if state == Qt.CheckState.Checked.value:
                # Yellow card was given
                name_btn = table.cellWidget(row, 2)
                player_name = name_btn.text() if name_btn else "Unknown Player"

                print(f"Yellow card given to {player_name} ({team_type} team)")

                # Uncheck red card (mutual exclusion)
                red_widget = table.cellWidget(row, 4)
                if red_widget:
                    red_cb = red_widget.findChild(QCheckBox)
                    if red_cb and red_cb.isChecked():
                        red_cb.setChecked(False)

                # Show confirmation message
                print(
                    f"✅ {team_type.title()} team: Yellow card given to {player_name}"
                )

                # Do not auto-create a new row on toggle
                # Update aggregated card stats and enforce fouls minimum
                self.update_card_stats(team_type)

            else:
                # Yellow card was removed
                print(f"Yellow card removed for {team_type} team")
                # Recompute stats from current table state so fouls and cards decrease correctly
                self.update_card_stats(team_type)

        except Exception as e:
            print(f"Error in on_yellow_card_changed: {e}")

    def on_red_card_changed(self, state, team_type, row, table):
        """Handle red card checkbox state change"""
        try:
            from PySide6.QtCore import Qt

            if state == Qt.CheckState.Checked.value:
                # Red card was given
                name_btn = table.cellWidget(row, 2)
                player_name = name_btn.text() if name_btn else "Unknown Player"

                print(f"Red card given to {player_name} ({team_type} team)")

                # Uncheck yellow card (mutual exclusion)
                yellow_widget = table.cellWidget(row, 3)
                if yellow_widget:
                    yellow_cb = yellow_widget.findChild(QCheckBox)
                    if yellow_cb and yellow_cb.isChecked():
                        yellow_cb.setChecked(False)

                # Show confirmation message
                print(f"✅ {team_type.title()} team: Red card given to {player_name}")

                # Do not auto-create a new row on toggle
                # Update aggregated card stats and enforce fouls minimum
                self.update_card_stats(team_type)
                jersey_no = ""
                num_item = table.item(row, 1)
                if num_item:
                    jersey_no = num_item.text().strip()
                self._set_card_row_sent_off_state(table, row, True)
                entity_type = "player" if jersey_no else "official"
                self._mark_player_sent_off(
                    team_type,
                    jersey_no,
                    True,
                    player_name=player_name,
                    entity_type=entity_type,
                )

            else:
                # Red card was removed
                print(f"Red card removed for {team_type} team")
                # Recompute stats from current table state so fouls and cards decrease correctly
                self.update_card_stats(team_type)
                jersey_no = ""
                num_item = table.item(row, 1)
                if num_item:
                    jersey_no = num_item.text().strip()
                self._set_card_row_sent_off_state(table, row, False)
                entity_type = "player" if jersey_no else "official"
                self._mark_player_sent_off(
                    team_type,
                    jersey_no,
                    False,
                    player_name=player_name,
                    entity_type=entity_type,
                )

        except Exception as e:
            print(f"Error in on_red_card_changed: {e}")

    def _set_card_row_sent_off_state(
        self, table: QTableWidget, row: int, sent_off: bool
    ):
        """Visual hint inside the cards table when a player receives a red card."""
        try:
            num_item = table.item(row, 1)
            if num_item:
                color = (
                    QColor("#ff4d4f") if sent_off else QColor(CONFIG["colors"]["text"])
                )
                num_item.setForeground(color)
        except Exception as exc:
            print(f"Error highlighting card row {row}: {exc}")

    def _mark_player_sent_off(
        self,
        team_type: str,
        jersey_no: str,
        sent_off: bool,
        player_name: str | None = None,
        entity_type: str | None = None,
    ):
        """Notify other tabs that a player or official has been sent off."""
        try:
            if not team_type:
                return
            normalized = "home" if str(team_type).lower().startswith("home") else "away"
            resolved_type = entity_type
            if resolved_type not in {"player", "official"}:
                resolved_type = "player" if jersey_no else "official"
            if not jersey_no and not player_name:
                return

            if resolved_type == "player" and jersey_no:
                player_set = self.sent_off_players.setdefault(normalized, set())
                if sent_off:
                    player_set.add(jersey_no)
                else:
                    player_set.discard(jersey_no)
            elif resolved_type == "official" and player_name:
                official_set = self.sent_off_officials.setdefault(normalized, set())
                if sent_off:
                    official_set.add(player_name)
                else:
                    official_set.discard(player_name)

            main_window = self.window()
            if not main_window:
                return
            subs_tab = getattr(main_window, "subs_penalty_tab", None)
            if subs_tab and hasattr(subs_tab, "handle_sent_off_player_from_play_on"):
                try:
                    subs_tab.handle_sent_off_player_from_play_on(
                        normalized,
                        jersey_no,
                        sent_off,
                        player_name=player_name,
                        entity_type=resolved_type,
                    )
                except Exception as handler_exc:
                    print(
                        f"Error notifying Subs & Penalty tab about sent off entity: {handler_exc}"
                    )
        except Exception as exc:
            print(f"Error tracking sent off player: {exc}")

    def _get_card_button_text(self, widget) -> str:
        """Extract the button text for card table cells."""
        try:
            if widget is None:
                return ""
            if isinstance(widget, QPushButton):
                return widget.text()
            btn = widget.findChild(QPushButton)
            return btn.text() if btn else ""
        except Exception:
            return ""

    def _is_card_row_complete(self, table: QTableWidget, row: int) -> bool:
        """A card row is considered complete once a player and jersey number exist."""
        try:
            num_text = table.item(row, 1).text().strip() if table.item(row, 1) else ""
            name_text = self._get_card_button_text(table.cellWidget(row, 2))
            return bool(num_text and name_text and name_text != "Select Player")
        except Exception:
            return False

    def _are_card_rows_complete(self, table: QTableWidget) -> bool:
        """Ensure every existing card row is filled before adding another."""
        try:
            for row in range(table.rowCount()):
                if not self._is_card_row_complete(table, row):
                    return False
            return True
        except Exception:
            return False

    def add_card_row(self, table, team_type):
        """Add a new row to the card table when + button is clicked"""
        try:
            try:
                print(f"DEBUG add_card_row: clicked for team_type={team_type}")
            except Exception:
                pass
            if not self._are_card_rows_complete(table):
                QMessageBox.warning(
                    self,
                    "Incomplete Card Entry",
                    "Please fill the current card row before adding a new one.",
                )
                return
            # Get current row count
            current_rows = table.rowCount()

            # Add one new row
            table.setRowCount(current_rows + 1)
            new_row = current_rows

            # Initialize the new row with the same structure as existing rows
            self._initialize_single_card_row(table, new_row, team_type)
            print(f"Added new card row for {team_type} team")
        except Exception as e:
            print(f"Error in add_card_row: {e}")

    def _initialize_single_card_row(self, table, row, team_type):
        """Initialize a single card row with all necessary widgets"""
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QFont
            from PySide6.QtWidgets import (
                QButtonGroup,
                QCheckBox,
                QHBoxLayout,
                QPushButton,
            )

            # Time item - use running clock like scorer panel
            current_time = (
                self.get_current_time_text()
                if hasattr(self, "get_current_time_text")
                else (
                    self.timer_label.text() if hasattr(self, "timer_label") else "00:00"
                )
            )
            try:
                print(
                    f"DEBUG _initialize_single_card_row: row={row}, time={current_time}"
                )
            except Exception:
                pass
            time_item = QTableWidgetItem(current_time)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            time_item.setFont(QFont("Verdana", 12))
            table.setItem(row, 0, time_item)

            # Num item
            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(row, 1, num_item)

            # Name button
            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_default"]};
                    color: {CONFIG["colors"]["text"]};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            name_btn.clicked.connect(
                lambda checked, r=row: self.show_card_player_list(table, r, team_type)
            )
            table.setCellWidget(row, 2, name_btn)

            # Yellow card checkbox
            card_group = QButtonGroup(table)
            yellow_cb = QCheckBox()
            yellow_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FFFF00;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            yellow_cb.setEnabled(False)
            card_group.addButton(yellow_cb)
            yellow_cb.stateChanged.connect(
                lambda state, r=row: self.on_yellow_card_changed(
                    state, team_type, r, table
                )
            )
            yellow_cb.stateChanged.connect(
                lambda state, t=team_type: self.update_card_stats(t)
            )
            yellow_widget = QWidget()
            yellow_widget.setStyleSheet("border: 0px;")
            yellow_layout = QHBoxLayout(yellow_widget)
            yellow_layout.addWidget(yellow_cb)
            yellow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            yellow_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 3, yellow_widget)

            # Red card checkbox
            red_cb = QCheckBox()
            red_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            red_cb.setEnabled(False)
            card_group.addButton(red_cb)
            red_cb.stateChanged.connect(
                lambda state, r=row: self.on_red_card_changed(
                    state, team_type, r, table
                )
            )
            red_cb.stateChanged.connect(
                lambda state, t=team_type: self.update_card_stats(t)
            )
            red_widget = QWidget()
            red_widget.setStyleSheet("border: 0px;")
            red_layout = QHBoxLayout(red_widget)
            red_layout.addWidget(red_cb)
            red_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            red_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 4, red_widget)

            # Export checkbox
            export_cb = QCheckBox()
            export_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #10B981;
                    border: 1px solid #059669;
                    border-radius: 2px;
                }
            """)
            export_cb.setEnabled(True)
            export_widget = QWidget()
            export_widget.setStyleSheet("border: 0px;")
            export_layout = QHBoxLayout(export_widget)
            export_layout.addWidget(export_cb)
            export_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            export_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 5, export_widget)

            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            lock_cb.setEnabled(False)
            lock_cb.stateChanged.connect(
                lambda state, r=row: self.toggle_card_row_lock(table, r, state)
            )
            lock_widget = QWidget()
            lock_widget.setStyleSheet("border: 0px;")
            lock_layout = QHBoxLayout(lock_widget)
            lock_layout.addWidget(lock_cb)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 6, lock_widget)

            # Reset button
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            reset_btn.setProperty("table", table)
            reset_btn.clicked.connect(self._on_cards_reset_clicked)
            table.setCellWidget(row, 7, reset_btn)

        except Exception as e:
            print(f"Error in _initialize_single_card_row: {e}")

    def _on_cards_reset_clicked(self):
        try:
            sender = self.sender()
            if sender is None:
                print("DEBUG _on_cards_reset_clicked: no sender")
                return
            table = sender.property("table")
            if table is None:
                print("DEBUG _on_cards_reset_clicked: no table property on sender")
                return
            # Determine team type for stats update after deletion
            team_type = (
                "home" if table is getattr(self, "home_card_table", None) else "away"
            )
            for r in range(table.rowCount()):
                for c in range(table.columnCount()):
                    w = table.cellWidget(r, c)
                    if w is None:
                        continue
                    if w is sender:
                        table.removeRow(r)
                        print(
                            f"DEBUG _on_cards_reset_clicked: removed row {r} (direct)"
                        )
                        # Recalculate stats so cards from this row are removed
                        if hasattr(self, "update_card_stats"):
                            self.update_card_stats(team_type)
                        return
                    from PySide6.QtWidgets import QPushButton

                    if isinstance(w, QPushButton) and w is sender:
                        table.removeRow(r)
                        print(
                            f"DEBUG _on_cards_reset_clicked: removed row {r} (button cell)"
                        )
                        if hasattr(self, "update_card_stats"):
                            self.update_card_stats(team_type)
                        return
                    for btn in w.findChildren(QPushButton):
                        if btn is sender:
                            table.removeRow(r)
                            print(
                                f"DEBUG _on_cards_reset_clicked: removed row {r} (descendant)"
                            )
                            if hasattr(self, "update_card_stats"):
                                self.update_card_stats(team_type)
                            return
            print("DEBUG _on_cards_reset_clicked: sender not found in any cell")
        except Exception as e:
            print(f"Error _on_cards_reset_clicked: {e}")

    def update_card_stats(self, team_type: str):
        """Recalculate and update Match Statistics from cards tables.
        Promotion rule: Only two yellows FOR THE SAME PLAYER promote to one red."""
        try:

            def count_cards_with_promotion(tbl):
                total_yellow = 0
                direct_red = 0
                # Count yellows per player so promotion applies per-player, not globally
                yellows_per_player = {}
                player_meta = {}
                direct_red_entities = []
                if not tbl:
                    return 0, 0, 0, [], []
                for i in range(tbl.rowCount()):
                    # Player identity: prefer jersey number + name
                    num_item = tbl.item(i, 1)
                    num_text = num_item.text().strip() if num_item else ""
                    name_btn = tbl.cellWidget(i, 2)
                    name_text = name_btn.text().strip() if name_btn else ""
                    player_key = (
                        f"{num_text}|{name_text}"
                        if (num_text or name_text)
                        else f"row{i}"
                    )
                    player_meta[player_key] = {"num": num_text, "name": name_text}

                    # Yellow
                    yw = tbl.cellWidget(i, 3)
                    if yw:
                        ycb = yw.findChild(QCheckBox)
                        if ycb and ycb.isChecked():
                            total_yellow += 1
                            yellows_per_player[player_key] = (
                                yellows_per_player.get(player_key, 0) + 1
                            )

                    # Red (direct)
                    rw = tbl.cellWidget(i, 4)
                    if rw:
                        rcb = rw.findChild(QCheckBox)
                        if rcb and rcb.isChecked():
                            direct_red += 1
                            direct_red_entities.append(
                                {"num": num_text, "name": name_text}
                            )

                promoted_red = sum(count // 2 for count in yellows_per_player.values())
                double_yellow_entities = []
                for key, count in yellows_per_player.items():
                    if count >= 2:
                        meta = player_meta.get(key, {})
                        double_yellow_entities.append(
                            {
                                "num": meta.get("num", ""),
                                "name": meta.get("name", ""),
                            }
                        )
                return (
                    total_yellow,
                    direct_red,
                    promoted_red,
                    direct_red_entities,
                    double_yellow_entities,
                )

            tbl = self.home_card_table if team_type == "home" else self.away_card_table
            prev_y = self.stats_data.get(f"{team_type}_yellow_cards", 0)
            prev_r = self.stats_data.get(f"{team_type}_red_cards", 0)
            prev_total_cards = prev_y + prev_r

            (
                y_count,
                r_direct,
                r_promoted,
                direct_red_entities,
                double_yellow_entities,
            ) = count_cards_with_promotion(tbl)
            # Only promote pairs of yellows for the same player
            r_count = r_direct + r_promoted
            total_cards = y_count + r_count

            # Update backing stats so any later refresh keeps the same totals
            y_key = f"{team_type}_yellow_cards"
            r_key = f"{team_type}_red_cards"
            f_key = f"{team_type}_fouls"
            self.stats_data[y_key] = y_count
            self.stats_data[r_key] = r_count
            # Adjust fouls by the delta in total cards rather than forcing an exact match
            delta_cards = total_cards - prev_total_cards
            self.stats_data[f_key] = max(0, self.stats_data.get(f_key, 0) + delta_cards)

            # Push the recalculated values through the normal display/update path
            if hasattr(self, "stats_widgets"):
                self.update_stat_display("yellow_cards", team_type)
                self.update_stat_display("red_cards", team_type)
                self.update_stat_display("fouls", team_type)

            # Apply sent-off state to substitution tab based on cards
            sent_off_entities = list(direct_red_entities) + list(double_yellow_entities)
            self._apply_cards_sent_off(team_type, sent_off_entities)

            # Highlight card table rows in red for sent-off players (including double yellows)
            self._update_card_table_highlighting(tbl, sent_off_entities)

            try:
                print(
                    "DEBUG update_card_stats: "
                    f"team={team_type}, yellow_total={y_count}, red_direct={r_direct}, "
                    f"red_promoted={r_promoted}, red_total={r_count}, fouls_adjusted={self.stats_data.get(f_key, 0)}"
                )
            except Exception:
                pass
        except Exception as e:
            print(f"Error update_card_stats: {e}")

    def _update_card_table_highlighting(
        self, table: QTableWidget, sent_off_entities: list[dict]
    ):
        """Highlight card table rows in red for all sent-off players (direct red or double yellow)."""
        try:
            if not table:
                return

            # Get set of sent-off jersey numbers
            sent_off_numbers = {
                entity.get("num") for entity in sent_off_entities if entity.get("num")
            }

            # Update all rows in the table
            for row in range(table.rowCount()):
                num_item = table.item(row, 1)
                if not num_item:
                    continue

                jersey_no = num_item.text().strip()
                if jersey_no in sent_off_numbers:
                    # This player is sent off - highlight in red
                    self._set_card_row_sent_off_state(table, row, True)
                else:
                    # This player is not sent off - remove red highlighting
                    self._set_card_row_sent_off_state(table, row, False)
        except Exception as exc:
            print(f"Error updating card table highlighting: {exc}")

    def _apply_cards_sent_off(
        self, team_type: str, current_sent_off_entities: list[dict]
    ):
        """Ensure sent-off state from cards (direct reds or double yellows) stays in sync across tabs."""
        try:
            current_numbers = {
                entity.get("num")
                for entity in current_sent_off_entities
                if entity.get("num")
            }
            current_names = {
                entity.get("name")
                for entity in current_sent_off_entities
                if not entity.get("num") and entity.get("name")
            }

            previous_numbers = self.cards_sent_off_players.get(team_type, set())
            previous_names = self.cards_sent_off_officials.get(team_type, set())

            for jersey in current_numbers - previous_numbers:
                print(
                    f"[DEBUG _apply_cards_sent_off] Marking player sent OFF: team={team_type}, jersey={jersey}"
                )
                self._mark_player_sent_off(
                    team_type, jersey, True, entity_type="player"
                )
            for jersey in previous_numbers - current_numbers:
                print(
                    f"[DEBUG _apply_cards_sent_off] Marking player sent back ON: team={team_type}, jersey={jersey}"
                )
                self._mark_player_sent_off(
                    team_type, jersey, False, entity_type="player"
                )

            for name in current_names - previous_names:
                self._mark_player_sent_off(
                    team_type, "", True, player_name=name, entity_type="official"
                )
            for name in previous_names - current_names:
                self._mark_player_sent_off(
                    team_type, "", False, player_name=name, entity_type="official"
                )

            self.cards_sent_off_players[team_type] = set(current_numbers)
            self.cards_sent_off_officials[team_type] = set(current_names)
        except Exception as exc:
            print(f"Error applying cards sent off state: {exc}")

    def add_new_card_row(self, table, team_type):
        """Add a new row to the card table for the next card assignment"""
        try:
            # Get current row count
            current_rows = table.rowCount()

            # Add one new row
            table.setRowCount(current_rows + 1)
            new_row = current_rows

            # Time item - use running clock like scorer panel
            current_time = self.get_current_time_text()
            try:
                print(f"DEBUG add_new_card_row: new_row={new_row}, time={current_time}")
            except Exception:
                pass
            time_item = QTableWidgetItem(current_time)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            time_item.setFont(QFont("Verdana", 12))
            table.setItem(new_row, 0, time_item)

            # Number item
            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(new_row, 1, num_item)

            # Name button
            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONFIG["colors"]["button_default"]};
                    color: {CONFIG["colors"]["text"]};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {CONFIG["colors"]["hover"]}; }}
            """)
            name_btn.clicked.connect(
                lambda checked, r=new_row: self.show_card_player_list(
                    table, r, team_type
                )
            )
            # When selecting player, set current time for this row similar to scorer panels
            # Current time source: if PlayOnTab exposes a method get_current_time, use it; else fallback to "00:00"
            try:
                if hasattr(self, "get_current_time") and callable(
                    self.get_current_time
                ):
                    current_time = self.get_current_time()
                else:
                    current_time = "00:00"
                ti = table.item(new_row, 0)
                if ti:
                    ti.setText(current_time)
            except Exception:
                pass
            name_btn.clicked.connect(
                lambda checked, r=new_row: self.show_card_player_list(
                    table, r, team_type
                )
            )
            try:
                if hasattr(self, "get_current_time") and callable(
                    self.get_current_time
                ):
                    current_time = self.get_current_time()
                else:
                    current_time = "00:00"
                ti = table.item(new_row, 0)
                if ti:
                    ti.setText(current_time)
            except Exception:
                pass
            table.setCellWidget(new_row, 2, name_btn)

            # Yellow card checkbox
            card_group = QButtonGroup(table)
            yellow_cb = QCheckBox()
            yellow_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FFFF00;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            yellow_cb.setEnabled(False)  # Disable initially
            card_group.addButton(yellow_cb)
            yellow_cb.stateChanged.connect(
                lambda state,
                t=team_type,
                r=new_row,
                tbl=table: self.on_yellow_card_changed(state, t, r, tbl)
            )
            yellow_widget = QWidget()
            yellow_widget.setStyleSheet("border: 0px;")
            yellow_layout = QHBoxLayout(yellow_widget)
            yellow_layout.addWidget(yellow_cb)
            yellow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            yellow_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(new_row, 3, yellow_widget)

            # Red card checkbox
            red_cb = QCheckBox()
            red_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            red_cb.setEnabled(False)  # Disable initially
            card_group.addButton(red_cb)
            red_cb.stateChanged.connect(
                lambda state,
                t=team_type,
                r=new_row,
                tbl=table: self.on_red_card_changed(state, t, r, tbl)
            )
            red_widget = QWidget()
            red_widget.setStyleSheet("border: 0px;")
            red_layout = QHBoxLayout(red_widget)
            red_layout.addWidget(red_cb)
            red_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            red_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(new_row, 4, red_widget)

            # Select checkbox
            select_cb = QCheckBox()
            select_cb.setStyleSheet("""
                QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; }
                QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }
            """)
            select_widget = QWidget()
            select_widget.setStyleSheet("border: 0px;")
            select_layout = QHBoxLayout(select_widget)
            select_layout.addWidget(select_cb)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(new_row, 5, select_widget)

            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
            """)
            lock_cb.setEnabled(False)  # Disable initially
            lock_cb.stateChanged.connect(
                lambda state, r=new_row: self.toggle_card_row_lock(table, r, state)
            )
            lock_widget = QWidget()
            lock_widget.setStyleSheet("border: 0px;")
            lock_layout = QHBoxLayout(lock_widget)
            lock_layout.addWidget(lock_cb)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(new_row, 6, lock_widget)

            # Reset button
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: white;
                    border: 1px solid #B91C1C;
                    border-radius: 3px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: #EF4444;
                }
            """)
            reset_btn.setProperty("table", table)
            reset_btn.clicked.connect(self._on_cards_reset_clicked)
            table.setCellWidget(new_row, 7, reset_btn)

            print(f" Added new card row {new_row + 1} for {team_type} team")

        except Exception as e:
            print(f"Error adding new card row: {e}")
            import traceback

            traceback.print_exc()
