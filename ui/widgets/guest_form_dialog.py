"""
Guest Form Dialog for entering guest data
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class GuestFormDialog(QDialog):
    """Dialog for entering guest information"""

    guest_saved = Signal(dict)  # Emitted when guest data is saved

    def __init__(self, guest_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.guest_data = guest_data or {}
        self.setup_ui()
        self.populate_form()

    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Guest Information")
        self.setModal(True)
        self.setFixedSize(400, 300)

        # Set dialog style
        self.setStyleSheet("""
            QDialog {
                background: #0f172a;
                border: 2px solid #243057;
                border-radius: 12px;
            }
            QLabel {
                color: #f3f4f6;
                font-weight: bold;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background: #1f2937;
                color: #f3f4f6;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #10b981;
            }
            QGroupBox {
                color: #e5e7eb;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #2e3a55;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background: transparent;
            }
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Guest Information Form")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #f8fafc;
                background: #111827;
                border: 1px solid #243057;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 5px;
            }
        """)
        title_label.setFixedHeight(40)
        layout.addWidget(title_label)

        # Simple form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Full Name field
        self.full_name_edit = QLineEdit()
        self.full_name_edit.setPlaceholderText("Enter full name")
        self.full_name_edit.setMinimumHeight(40)
        form_layout.addRow("Full Name:", self.full_name_edit)

        # Guest Type field
        self.guest_type_edit = QLineEdit()
        self.guest_type_edit.setPlaceholderText(
            "Enter guest type (e.g., VIP Guest, Chief Guest)"
        )
        self.guest_type_edit.setMinimumHeight(40)
        form_layout.addRow("Guest Type:", self.guest_type_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("Save Guest")
        self.save_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.save_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #047857);
                color: white;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #065f46);
            }
        """)
        self.save_button.clicked.connect(self.save_guest)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b7280, stop:1 #4b5563);
                color: white;
                border: 1px solid #6b7280;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9ca3af, stop:1 #6b7280);
            }
        """)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def populate_form(self):
        """Populate form with existing guest data if available"""
        if not self.guest_data:
            return

        self.full_name_edit.setText(self.guest_data.get("full_name", ""))

        # Set guest type
        guest_type = self.guest_data.get("guest_type", "VIP Guest")
        self.guest_type_edit.setText(guest_type)

    def save_guest(self):
        """Save guest data and emit signal"""
        # Validate required fields
        if not self.full_name_edit.text().strip():
            self.show_validation_error("Full name is required")
            return

        # Collect form data
        guest_data = {
            "full_name": self.full_name_edit.text().strip(),
            "guest_type": self.guest_type_edit.text().strip() or "Guest",
        }

        print(f"Guest form saving data: {guest_data}")

        # Emit signal with guest data
        self.guest_saved.emit(guest_data)
        self.accept()

    def show_validation_error(self, message: str):
        """Show validation error message"""
        from PySide6.QtWidgets import QMessageBox

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Validation Error")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStyleSheet("""
            QMessageBox {
                background: #374151;
                color: white;
            }
            QMessageBox QPushButton {
                background: #4b5563;
                color: white;
                border: 1px solid #6b7280;
                border-radius: 4px;
                padding: 5px 15px;
            }
        """)
        msg_box.exec()
