"""
Modern UI Components for Football Score Pro 2.0
Custom styled components with professional appearance
"""

from typing import Optional

from PySide6.QtWidgets import QPushButton, QLabel, QWidget, QCheckBox, QVBoxLayout, QHBoxLayout, QLineEdit, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QFont


class ModernButton(QPushButton):
    """Custom modern button with hover effects and multiple styles"""

    def __init__(self, text: str = "", style_type: str = "primary", parent=None):
        super().__init__(text, parent)
        self.style_type = style_type
        self._custom_stylesheet: Optional[str] = None
        self.setMinimumHeight(35)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style()

    def apply_style(self):
        if self._custom_stylesheet:
            self.setStyleSheet(self._custom_stylesheet)
            return
        styles = self._get_button_styles()
        self.setStyleSheet(styles.get(self.style_type, styles["primary"]))

    def set_style_type(self, style_type: str):
        self.style_type = style_type
        self._custom_stylesheet = None
        self.apply_style()

    def set_custom_stylesheet(self, stylesheet: Optional[str]):
        """Allow external callers to fully override the button stylesheet."""
        self._custom_stylesheet = stylesheet
        if stylesheet:
            self.setStyleSheet(stylesheet)
        else:
            self.apply_style()

    def _get_button_styles(self) -> dict:
        return {
            "primary": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3b82f6, stop:1 #2563eb);
                    border: 1px solid #60a5fa;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1e40af, stop:1 #1e3a8a);
                    border: 1px solid #3b82f6;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2563eb, stop:1 #1d4ed8);
                }
                QPushButton:disabled {
                    background-color: #444;
                    color: #888;
                }
            """,
            "success": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #10b981, stop:1 #059669);
                    border: 1px solid #34d399;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #34d399, stop:1 #10b981);
                    border: 1px solid #6ee7b7;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #059669, stop:1 #047857);
                }
                QPushButton:disabled {
                    background-color: #444;
                    color: #888;
                }
            """,
            "danger": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ef4444, stop:1 #dc2626);
                    border: 1px solid #f87171;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f87171, stop:1 #ef4444);
                    border: 1px solid #fca5a5;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #dc2626, stop:1 #b91c1c);
                }
                QPushButton:disabled {
                    background-color: #444;
                    color: #888;
                }
            """,
            "secondary": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6b7280, stop:1 #4b5563);
                    border: 1px solid #9ca3af;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #9ca3af, stop:1 #6b7280);
                    border: 1px solid #d1d5db;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4b5563, stop:1 #374151);
                }
                QPushButton:disabled {
                    background-color: #444;
                    color: #888;
                }
            """,
        }


class ModernLabel(QLabel):
    """Custom modern label with typography styles"""

    def __init__(self, text: str = "", label_type: str = "body", parent=None):
        super().__init__(text, parent)
        self.label_type = label_type
        self.apply_style()

    def apply_style(self):
        styles = self._get_label_styles()
        self.setStyleSheet(styles.get(self.label_type, styles["body"]))

    def set_label_type(self, label_type: str):
        self.label_type = label_type
        self.apply_style()

    def _get_label_styles(self) -> dict:
        return {
            "heading": """
                QLabel {
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: 700;
                    margin: 10px 0;
                    letter-spacing: -0.5px;
                }
            """,
            "subheading": """
                QLabel {
                    color: #e5e7eb;
                    font-size: 15px;
                    font-weight: 600;
                    margin: 6px 0;
                    letter-spacing: -0.25px;
                }
            """,
            "body": """
                QLabel {
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.025em;
                }
            """,
            "muted": """
                QLabel {
                    color: #9ca3af;
                    font-size: 12px;
                    font-weight: 400;
                    letter-spacing: 0.025em;
                }
            """,
            "success": """
                QLabel {
                    color: #10b981;
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.025em;
                }
            """,
            "error": """
                QLabel {
                    color: #ef4444;
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.025em;
                }
            """,
            "color-code": """
                QLabel {
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: 600;
                    font-family: 'Courier New', monospace;
                    text-align: center;
                    padding: 2px 4px;
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid #4b5563;
                    border-radius: 4px;
                    margin: 0px 0px 4px 0px;
                    min-height: 16px;
                    max-height: 20px;
                }
            """,
        }


class ModernCheckbox(QWidget):
    """Custom modern checkbox widget with professional styling"""

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked = False
        self.setFixedSize(20, 20)  # Reduced size to ensure it fits in column
        self.setCursor(Qt.PointingHandCursor)
        # Make background transparent so container color shows through
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.checked:
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor("#10b981"))
            gradient.setColorAt(1, QColor("#047857"))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor("#10b981"), 2))
        else:
            painter.setBrush(QColor("#1f2937"))
            painter.setPen(QPen(QColor("#4b5563"), 2))
        
        painter.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 3, 3)
        
        if self.checked:
            painter.setPen(QPen(QColor('white'), 2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(4, 10, 7, 13)
            painter.drawLine(7, 13, 15, 5)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()

    def toggle(self) -> bool:
        self.checked = not self.checked
        self.update()
        self.toggled.emit(self.checked)
        return self.checked

    def isChecked(self) -> bool:
        return self.checked

    def setChecked(self, checked: bool):
        if self.checked != checked:
            self.checked = checked
            self.update()
            self.toggled.emit(self.checked)


class ModernSpinBox(QWidget):
    """Custom spin box with modern right-side arrows used across the app.

    Features:
    - Rounded input field with dark background
    - Two compact arrow buttons stacked on the right
    - Emits valueChanged(int)
    """

    valueChanged = Signal(int)

    def __init__(self, parent=None, minimum: int = 0, maximum: int = 9999, value: int = 0):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._value = max(self._min, min(value, self._max))
        # Make spinner compact; prevent layout from stretching it
        try:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        except AttributeError:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self.setFixedWidth(140)

        container = QHBoxLayout(self)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(0)

        self.input = QLineEdit(str(self._value), self)
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setFixedHeight(44)
        self.input.setFixedWidth(100)
        self.input.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.input.setStyleSheet(
            """
            QLineEdit {
                background-color: #374151;
                color: #ffffff;
                border: 1px solid #6b7280;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border-right: 1px solid #6b7280; /* inner divider */
                padding: 8px 12px;
                min-width: 100px;
                max-width: 100px;
            }
            QLineEdit:focus {
                border: 2px solid #10b981;
                background-color: #4b5563;
            }
            """
        )

        arrows = QVBoxLayout()
        arrows.setContentsMargins(0, 0, 0, 0)
        arrows.setSpacing(0)

        self.btn_up = ModernButton("\u25B2", "secondary", self)
        self.btn_up.setFixedSize(28, 22)
        self.btn_up.setStyleSheet(
            """
            QPushButton { 
                border-top-right-radius: 12px; 
                border-bottom-right-radius: 0px; 
                padding: 0; 
                min-height: 0; 
                font-size: 16px;
                font-weight: bold;
            }
            """
        )
        self.btn_down = ModernButton("\u25BC", "secondary", self)
        self.btn_down.setFixedSize(28, 22)
        self.btn_down.setStyleSheet(
            """
            QPushButton { 
                border-top-right-radius: 0px; 
                border-bottom-right-radius: 12px; 
                padding: 0; 
                min-height: 0; 
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        arrows.addWidget(self.btn_up)
        arrows.addWidget(self.btn_down)

        container.addWidget(self.input)
        container.addLayout(arrows)

        # Connections
        self.btn_up.clicked.connect(self.increment)
        self.btn_down.clicked.connect(self.decrement)
        self.input.editingFinished.connect(self._on_editing_finished)

    def value(self) -> int:
        return self._value

    def setRange(self, minimum: int, maximum: int):
        self._min = minimum
        self._max = maximum
        self.setValue(self._value)

    def setValue(self, value: int):
        clamped = max(self._min, min(int(value), self._max))
        if clamped != self._value:
            self._value = clamped
            self.input.setText(str(self._value))
            self.valueChanged.emit(self._value)
        else:
            self.input.setText(str(self._value))

    def increment(self):
        self.setValue(self._value + 1)

    def decrement(self):
        self.setValue(self._value - 1)

    def _on_editing_finished(self):
        text = self.input.text().strip()
        try:
            self.setValue(int(text))
        except ValueError:
            self.input.setText(str(self._value))
