"""
Dialog for configuring the application PIN.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QFont, QRegularExpressionValidator, QIcon

from src.constants import UIConstants, AppConstants


class SetPinDialog(QDialog):
    """Dialog allowing the user to change the lock/unlock PIN."""

    def __init__(self, current_pin: str, parent=None):
        super().__init__(parent)
        self._current_pin = (current_pin or AppConstants.DEFAULT_PIN).strip()
        self._new_pin = None
        self._visibility_actions = []
        self._eye_icon = None
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("Set PIN")
        self.setModal(True)
        self.setFixedSize(UIConstants.DIALOG_WIDTH, UIConstants.DIALOG_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(UIConstants.PADDING_NORMAL)
        layout.setContentsMargins(
            UIConstants.PADDING_LARGE, 
            UIConstants.PADDING_LARGE, 
            UIConstants.PADDING_LARGE, 
            UIConstants.PADDING_LARGE
        )

        title = QLabel("Update Security PIN")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont(
            UIConstants.FONT_FAMILY_MAIN, 
            UIConstants.FONT_SIZE_TITLE, 
            UIConstants.FONT_WEIGHT_BOLD
        ))
        title.setStyleSheet(f"color: {UIConstants.COLOR_TEXT_LIGHT};")
        layout.addWidget(title)

        validator = QRegularExpressionValidator(QRegularExpression(r"\d{0,4}"), self)

        self.current_pin_input = self._create_line_edit("Current PIN", validator)
        layout.addWidget(self.current_pin_input)

        self.new_pin_input = self._create_line_edit("New PIN (4 digits)", validator)
        layout.addWidget(self.new_pin_input)

        self.confirm_pin_input = self._create_line_edit("Confirm New PIN", validator)
        layout.addWidget(self.confirm_pin_input)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont(
            UIConstants.FONT_FAMILY_MAIN, 
            UIConstants.FONT_SIZE_NORMAL, 
            UIConstants.FONT_WEIGHT_BOLD
        ))
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {UIConstants.COLOR_BTN_CANCEL};
                color: white;
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_BORDER_DEFAULT};
                border-radius: {UIConstants.BORDER_RADIUS}px;
                padding: {UIConstants.PADDING_SMALL}px {UIConstants.PADDING_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {UIConstants.COLOR_BTN_CANCEL_HOVER};
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_BG_INPUT_FOCUS};
            }}
            QPushButton:pressed {{
                background-color: {UIConstants.COLOR_BTN_CANCEL_PRESSED};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save PIN")
        save_btn.setFont(QFont(
            UIConstants.FONT_FAMILY_MAIN, 
            UIConstants.FONT_SIZE_NORMAL, 
            UIConstants.FONT_WEIGHT_BOLD
        ))
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_PRIMARY};
                border-radius: {UIConstants.BORDER_RADIUS}px;
                padding: {UIConstants.PADDING_SMALL}px {UIConstants.PADDING_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 {UIConstants.COLOR_PRIMARY});
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {UIConstants.COLOR_PRIMARY}, stop:1 #1e3a8a);
            }}
        """)
        save_btn.clicked.connect(self._on_save_clicked)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.current_pin_input.setFocus()

    def _create_line_edit(self, placeholder: str, validator: QRegularExpressionValidator) -> QLineEdit:
        line_edit = QLineEdit()
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        line_edit.setPlaceholderText(placeholder)
        line_edit.setMaxLength(4)
        line_edit.setValidator(validator)
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line_edit.setFont(QFont(
            UIConstants.FONT_FAMILY_MAIN, 
            UIConstants.FONT_SIZE_LARGE, 
            UIConstants.FONT_WEIGHT_BOLD
        ))
        line_edit.setFixedHeight(46)
        line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {UIConstants.COLOR_BG_INPUT};
                color: {UIConstants.COLOR_TEXT_WHITE};
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_BORDER_DEFAULT};
                border-radius: {UIConstants.BORDER_RADIUS}px;
                padding: {UIConstants.PADDING_SMALL}px;
                font-size: 18px;
            }}
            QLineEdit:focus {{
                border: {UIConstants.BORDER_WIDTH}px solid {UIConstants.COLOR_BORDER_FOCUS};
                background-color: {UIConstants.COLOR_BG_INPUT_FOCUS};
            }}
        """)
        self._attach_visibility_toggle(line_edit)
        return line_edit

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
        """Attach an eye icon toggle to show/hide PIN values."""
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

    def _on_save_clicked(self):
        current = self.current_pin_input.text().strip()
        new_pin = self.new_pin_input.text().strip()
        confirm_pin = self.confirm_pin_input.text().strip()

        if current != self._current_pin and not (
            AppConstants.MASTER_PIN and current == AppConstants.MASTER_PIN
        ):
            QMessageBox.warning(self, "Incorrect PIN", "The current PIN you entered is incorrect.")
            self.current_pin_input.clear()
            self.current_pin_input.setFocus()
            return

        if len(new_pin) != 4 or not new_pin.isdigit():
            QMessageBox.warning(self, "Invalid PIN", "The new PIN must be exactly 4 digits.")
            self.new_pin_input.clear()
            self.confirm_pin_input.clear()
            self.new_pin_input.setFocus()
            return

        if new_pin != confirm_pin:
            QMessageBox.warning(self, "Mismatch", "New PIN and confirmation do not match.")
            self.confirm_pin_input.clear()
            self.confirm_pin_input.setFocus()
            return

        if new_pin == self._current_pin:
            QMessageBox.information(self, "No Change", "The new PIN is the same as the current PIN.")
            self.new_pin_input.clear()
            self.confirm_pin_input.clear()
            self.new_pin_input.setFocus()
            return

        self._new_pin = new_pin
        self.accept()

    def get_new_pin(self) -> str | None:
        """Return the new PIN chosen by the user."""
        return self._new_pin

