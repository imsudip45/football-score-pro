"""
Multi Guest Form Dialog - single dialog to edit all guest entries at once
"""

from typing import Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QWidget, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class MultiGuestFormDialog(QDialog):
    """Dialog for entering up to 6 guests in one place."""

    guests_saved = Signal(dict)  # Emits mapping like { 'guest1': {...}, ... }

    def __init__(self, existing_guests: Dict[str, Any] | None = None, parent=None):
        super().__init__(parent)
        self.existing_guests = existing_guests or {}
        self._edits: Dict[str, Dict[str, QLineEdit]] = {}
        self._setup_ui()
        self._populate_from_existing()

    def _setup_ui(self):
        self.setWindowTitle("Guests (All)")
        self.setModal(True)
        self.setFixedSize(820, 900)

        self.setStyleSheet(
            """
            QDialog {
                background: #0f172a;
                border: 2px solid #1f2a44;
                border-radius: 12px;
            }
            QLabel {
                color: #f3f4f6;
                font-weight: bold;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit {
                background: #111827;
                color: #f9fafb;
                border: 1px solid #1f2937;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #10b981;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea QWidget {
                background: transparent;
            }
            QPushButton {
                border-radius: 8px;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton#save {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #047857);
                color: white;
                border: 1px solid #10b981;
            }
            QPushButton#cancel {
                background: #374151;
                color: white;
                border: 1px solid #4b5563;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Guests Information (1 - 6)")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Scroll container for all rows
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Six stacked forms
        for i in range(1, 7):
            guest_id = f"guest{i}"
            row = QWidget(content)
            row.setStyleSheet("background: transparent;")
            form = QFormLayout(row)
            form.setContentsMargins(0, 0, 0, 0)
            form.setSpacing(6)
            try:
                form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            except Exception:
                form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

            name_edit = QLineEdit()
            name_edit.setPlaceholderText(f"Guest {i} full name")
            name_edit.setMinimumWidth(380)
            name_edit.setMinimumHeight(44)
            try:
                name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            except AttributeError:
                name_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            designation_edit = QLineEdit()
            designation_edit.setPlaceholderText("Designation (e.g., VIP Guest)")
            designation_edit.setMinimumWidth(380)
            designation_edit.setMinimumHeight(44)
            try:
                designation_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            except AttributeError:
                designation_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            form.addRow(QLabel(f"Guest {i} Name:"), name_edit)
            form.addRow(QLabel("Designation:"), designation_edit)

            content_layout.addWidget(row)
            self._edits[guest_id] = {"full_name": name_edit, "designation": designation_edit}

        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save All")
        btn_save.setObjectName("save")
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_save)
        layout.addLayout(buttons)

    def _populate_from_existing(self):
        for guest_id, fields in self._edits.items():
            data = self.existing_guests.get(guest_id, {}) or {}
            fields["full_name"].setText(str(data.get("full_name", "")))
            fields["designation"].setText(str(data.get("designation", data.get("guest_type", ""))))

    def _on_save(self):
        payload: Dict[str, Any] = {}
        for guest_id, fields in self._edits.items():
            name = fields["full_name"].text().strip()
            gtype = fields["designation"].text().strip()
            if name:
                payload[guest_id] = {"full_name": name, "designation": gtype or "Guest"}
        self.guests_saved.emit(payload)
        self.accept()


