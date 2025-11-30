"""
Color Panel Widget for FSP 2.0
Team color selection with single/double color modes
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QColorDialog, QFrame
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from .modern_components import ModernButton, ModernLabel


class ColorPanel(QWidget):
    """Panel for team color selection"""

    color_changed = Signal()

    def __init__(self, team_name: str, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.color_1 = "#000000"
        self.color_2 = "#000000"
        self.color_mode = "double"
        
        self.single_radio = None
        self.double_radio = None
        self.color_1_button = None
        self.color_2_button = None
        self.color_1_label = None
        self.color_2_label = None
        
        self.setup_ui()
        self.connect_signals()
        self.update_color_visibility()

    def setup_ui(self):
        """Setup the color panel UI"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 5, 6, 5)

        # Radios disabled: always show two colors
        self.single_radio = None
        self.double_radio = None

        # Color 1 button and label
        self.color_1_button = ModernButton("", "primary")
        layout.addWidget(self.color_1_button)

        self.color_1_label = ModernLabel(self.color_1, "color-code")
        self.color_1_label.setFixedHeight(20)
        layout.addWidget(self.color_1_label)

        # Color 2 button and label
        self.color_2_button = ModernButton("", "primary")
        layout.addWidget(self.color_2_button)

        self.color_2_label = ModernLabel(self.color_2, "color-code")
        self.color_2_label.setFixedHeight(20)
        layout.addWidget(self.color_2_label)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setFixedHeight(180)
        
        # Initialize button colors to match default color values
        if self.color_1_button:
            self.update_button_color(self.color_1_button, self.color_1)
        if self.color_2_button:
            self.update_button_color(self.color_2_button, self.color_2)

    def connect_signals(self):
        """Connect signals for color panel controls"""
        # No radio toggles; always double mode
        if self.color_1_button:
            self.color_1_button.clicked.connect(self.pick_color_1)
        if self.color_2_button:
            self.color_2_button.clicked.connect(self.pick_color_2)

    def pick_color_1(self):
        """Open color picker for color 1"""
        self.select_color(1, user_initiated=True)

    def pick_color_2(self):
        """Open color picker for color 2"""
        self.select_color(2, user_initiated=True)

    def select_color(self, color_index: int, user_initiated=True):
        """Open color picker dialog and update color"""
        if not user_initiated:
            return
        try:
            current_color = self.color_1 if color_index == 1 else self.color_2
            color = QColorDialog.getColor(QColor(current_color), self)
            if color.isValid():
                hex_color = color.name()
                if color_index == 1:
                    self.color_1 = hex_color
                    if self.color_1_button:
                        self.update_button_color(self.color_1_button, hex_color)
                    if self.color_1_label:
                        self.color_1_label.setText(hex_color)
                elif color_index == 2:
                    self.color_2 = hex_color
                    if self.color_2_button:
                        self.update_button_color(self.color_2_button, hex_color)
                    if self.color_2_label:
                        self.color_2_label.setText(hex_color)
                self.color_changed.emit()
        except Exception as e:
            print(f"Error selecting color for {self.team_name}: {e}")

    def update_button_color(self, button: ModernButton, color: str):
        """Update button background color"""
        try:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 1px solid #4b5563;
                    color: #ffffff;
                    padding: 8px 8px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {color};
                    opacity: 0.8;
                }}
                QPushButton:pressed {{
                    background: {color};
                    opacity: 0.6;
                }}
            """)
        except Exception as e:
            print(f"Error updating button color: {e}")

    def update_colors(self, color_1: str, color_2: str, color_mode: str):
        """Update color panel with provided colors"""
        try:
            self.color_1 = color_1
            self.color_2 = color_2
            # Force double mode regardless of input
            self.color_mode = "double"

            if self.color_1_button:
                self.update_button_color(self.color_1_button, color_1)
            if self.color_1_label:
                self.color_1_label.setText(color_1)

            if self.color_2_button:
                self.update_button_color(self.color_2_button, color_2)
            if self.color_2_label:
                self.color_2_label.setText(color_2)
                
            self.update_color_visibility()
        except Exception as e:
            print(f"Error updating colors for {self.team_name}: {e}")

    def get_colors(self) -> tuple:
        """Get current color settings"""
        return (self.color_1, self.color_2, "double")

    def update_color_visibility(self):
        """Update visibility of color buttons based on current mode"""
        # Always show both color controls
        if self.color_2_button:
            self.color_2_button.show()
        if self.color_2_label:
            self.color_2_label.show()

    def on_color_mode_changed(self, checked: bool):
        """Handle color mode radio button changes"""
        # Keep double mode permanently
        self.color_mode = "double"
        self.update_color_visibility()
        self.color_changed.emit()

    def get_radio_button_style(self) -> str:
        """Get radio button stylesheet"""
        return """
            QRadioButton {
                color: #e5e7eb;
                font-weight: 600;
                font-size: 12px;
                spacing: 8px;
                padding: 2px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #4b5563;
                background: #1f2937;
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 #10b981, stop:1 #059669);
                border: 2px solid #059669;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #6b7280;
            }
        """

