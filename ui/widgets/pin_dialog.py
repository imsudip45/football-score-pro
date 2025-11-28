"""
PIN Dialog for Lock/Unlock functionality
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QRegularExpression
from PySide6.QtGui import QFont, QRegularExpressionValidator, QIcon


class PinDialog(QDialog):
    """Dialog for entering PIN to lock/unlock the application"""
    
    pin_verified = Signal(bool)  # Emits True if PIN is correct
    
    def __init__(self, is_locked: bool, parent=None, correct_pin: str = "2580", lock_type: str = "reset"):
        super().__init__(parent)
        self.is_locked = is_locked
        self.correct_pin = (correct_pin or "2580").strip()
        self.lock_type = lock_type  # "reset" or "master"
        self._visibility_actions = []
        self._eye_icon = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the PIN dialog UI"""
        self.setWindowTitle("Enter PIN")
        self.setModal(True)
        self.setFixedSize(350, 200)
        
        # Set window flags to make it a proper dialog
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label - different text based on lock type
        if self.lock_type == "master":
            title_text = "Unlock Application" if self.is_locked else "Lock Application"
        else:
            title_text = "Unlock Reset Match" if self.is_locked else "Lock Reset Match"
        
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Verdana", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #e5e7eb;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # PIN input field
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setMaxLength(4)
        self.pin_input.setFont(QFont("Verdana", 16, QFont.Weight.Bold))
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setFixedHeight(45)
        regex = QRegularExpression(r"\d{0,4}")
        self.pin_input.setValidator(QRegularExpressionValidator(regex, self.pin_input))
        self.pin_input.setStyleSheet("""
            QLineEdit {
                background-color: #1f2937;
                color: #ffffff;
                border: 2px solid #4b5563;
                border-radius: 8px;
                padding: 8px;
                font-size: 18px;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #374151;
            }
        """)
        self.pin_input.returnPressed.connect(self.verify_pin)
        self._attach_visibility_toggle(self.pin_input)
        layout.addWidget(self.pin_input)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Verdana", 11, QFont.Weight.Bold))
        cancel_button.setFixedHeight(40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: 2px solid #4b5563;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border: 2px solid #374151;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        # Verify button
        verify_button = QPushButton("Verify" if self.is_locked else "Lock")
        verify_button.setFont(QFont("Verdana", 11, QFont.Weight.Bold))
        verify_button.setFixedHeight(40)
        verify_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: 2px solid #047857;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
                border: 2px solid #065f46;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #065f46);
            }
        """)
        verify_button.clicked.connect(self.verify_pin)
        buttons_layout.addWidget(verify_button)
        
        layout.addLayout(buttons_layout)
        
        # Set focus to PIN input
        self.pin_input.setFocus()
    
    def _get_eye_icon(self) -> QIcon | None:
        """Load and cache the eye icon used for visibility toggles."""
        if self._eye_icon is not None:
            return self._eye_icon
        eye_path = Path(__file__).resolve().parent.parent.parent / "resources" / "images" / "eye.png"
        if eye_path.exists():
            self._eye_icon = QIcon(str(eye_path))
        else:
            self._eye_icon = None
        return self._eye_icon

    def _attach_visibility_toggle(self, line_edit: QLineEdit):
        """Attach an eye icon toggle to show/hide the PIN."""
        icon = self._get_eye_icon()
        if not icon:
            return
        action = line_edit.addAction(icon, QLineEdit.ActionPosition.TrailingPosition)
        action.setCheckable(True)
        action.setToolTip("Show/Hide PIN")
        action.toggled.connect(
            lambda checked, le=line_edit: le.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        action.setChecked(False)
        self._visibility_actions.append(action)
        
    def verify_pin(self):
        """Verify the entered PIN"""
        entered_pin = self.pin_input.text().strip()
        
        if entered_pin == self.correct_pin:
            self.pin_verified.emit(True)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Invalid PIN",
                "The PIN you entered is incorrect. Please try again."
            )
            self.pin_input.clear()
            self.pin_input.setFocus()

