"""
Key Mapping Dialog for Football Score Pro
Allows users to configure keyboard shortcuts for various actions
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QGridLayout, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QKeyEvent


class KeyCaptureWidget(QLineEdit):
    """Custom widget for capturing key combinations"""
    
    key_captured = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Press key combination...")
        self.setFixedHeight(25)
        self.setMaximumHeight(25)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #374151;
                color: #ffffff;
                font-size: 12px;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.capturing = False
        
    def keyPressEvent(self, event):
        """Handle key press events to capture combinations"""
        if not self.capturing:
            self.capturing = True
            self.setText("Press key combination...")
            
        # Build the key combination string
        modifiers = []
        if event.modifiers() & Qt.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.MetaModifier:
            modifiers.append("Meta")
            
        # Get the base key
        key = event.key()
        key_text = ""
        
        # Handle modifier-only presses first
        if key == Qt.Key_Control or key == Qt.Key_Alt or key == Qt.Key_Shift or key == Qt.Key_Meta:
            # If only modifiers are pressed, show just the modifier
            if len(modifiers) == 1:
                combination = modifiers[0]
            else:
                combination = "+".join(modifiers)
        # Handle special keys
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            key_text = "Return"
        elif key == Qt.Key_Space:
            key_text = "Space"
        elif key == Qt.Key_Tab:
            key_text = "Tab"
        elif key == Qt.Key_Backspace:
            key_text = "Backspace"
        elif key == Qt.Key_Delete:
            key_text = "Delete"
        elif key == Qt.Key_Escape:
            key_text = "Escape"
        elif key >= Qt.Key_F1 and key <= Qt.Key_F12:
            key_text = f"F{key - Qt.Key_F1 + 1}"
        elif key >= Qt.Key_A and key <= Qt.Key_Z:
            key_text = chr(key)
        elif key >= Qt.Key_0 and key <= Qt.Key_9:
            key_text = chr(key)
        else:
            # For other keys, try to get the text representation
            key_text = event.text()
            if not key_text:
                # Skip unknown key codes to avoid showing cryptic numbers
                return
                
        # Combine modifiers and key
        if key_text:  # Only if we have a valid key
            if modifiers:
                combination = "+".join(modifiers + [key_text])
            else:
                combination = key_text
        elif modifiers and not key_text:
            # Modifier-only press
            combination = "+".join(modifiers)
        else:
            # Skip invalid combinations
            return
            
        self.setText(combination)
        self.key_captured.emit(combination)
        self.capturing = False
        
    def mousePressEvent(self, event):
        """Start capturing when clicked"""
        self.capturing = True
        self.setText("Press key combination...")
        self.setFocus()
        super().mousePressEvent(event)


class KeyMappingDialog(QDialog):
    """Dialog for configuring keyboard shortcuts"""
    
    # Signal emitted when key mappings change
    key_mapping_changed = Signal(dict)
    
    def __init__(self, parent=None, current_mappings=None):
        super().__init__(parent)
        self.current_mappings = current_mappings or {}
        self.setup_ui()
        self.load_current_mappings()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Key Mapping Configuration")
        self.setModal(True)
        self.setFixedSize(600, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Configure Keyboard Shortcuts")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8);
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Key mappings table
        self.mappings_table = QTableWidget()
        self.mappings_table.setColumnCount(3)
        self.mappings_table.setHorizontalHeaderLabels(["Action", "Current Key", "New Key"])
        self.mappings_table.horizontalHeader().setStretchLastSection(True)
        self.mappings_table.setAlternatingRowColors(True)
        self.mappings_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Store key capture widgets for each row
        self.key_capture_widgets = []
        
        # Style the table
        self.mappings_table.setStyleSheet("""
            QTableWidget {
                background-color: #1f2937;
                color: #ffffff;
                border: 1px solid #374151;
                border-radius: 8px;
                gridline-color: #374151;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #374151;
            }
            QTableWidget::item:selected {
                background-color: #3b82f6;
            }
            QHeaderView::section {
                background-color: #374151;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }
           
        """)
        
        # Set column widths
        header = self.mappings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Set row height to fit the widgets properly with some margin
        self.mappings_table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.mappings_table)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Reset to defaults button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: 2px solid #b91c1c;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ef4444;
                border-color: #dc2626;
            }
        """)
        reset_button.clicked.connect(self.reset_to_defaults)
        buttons_layout.addWidget(reset_button)
        
        buttons_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: 2px solid #4b5563;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9ca3af;
                border-color: #6b7280;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: 2px solid #047857;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #10b981;
                border-color: #059669;
            }
        """)
        apply_button.clicked.connect(self.apply_mappings)
        buttons_layout.addWidget(apply_button)
        
        layout.addLayout(buttons_layout)
        
        # Connect table cell changes
        self.mappings_table.cellChanged.connect(self.on_cell_changed)
        
    def load_current_mappings(self):
        """Load current key mappings into the table"""
        # Define available actions and their default keys
        actions = [
            ("Home Possession Toggle", "1"),
            ("Away Possession Toggle", "2"),
                ("Start Timer", "S"),
                ("Stop Timer", "T"),
                ("Reset Match", "r"),
                ("Home Goal +", "H"),
                ("Away Goal +", "A"),
                ("Home Goal -", "Shift+H"),
                ("Away Goal -", "Shift+A"),
        ]
        
        self.mappings_table.setRowCount(len(actions))
        
        for row, (action, default_key) in enumerate(actions):
            # Action column
            action_item = QTableWidgetItem(action)
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
            self.mappings_table.setItem(row, 0, action_item)
            
            # Current key column
            current_key = self.current_mappings.get(action, default_key)
            current_item = QTableWidgetItem(current_key)
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.mappings_table.setItem(row, 1, current_item)
            
            # New key column - use custom key capture widget
            key_capture = KeyCaptureWidget()
            key_capture.setText(current_key)
            key_capture.key_captured.connect(lambda key, r=row: self.on_key_captured(r, key))
            # Ensure the widget is properly sized and constrained within the cell
            from PySide6.QtWidgets import QSizePolicy
            key_capture.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.mappings_table.setCellWidget(row, 2, key_capture)
            self.key_capture_widgets.append(key_capture)
            
    def _is_duplicate_key(self, key_combination, current_row):
        """Check if the key combination is already used by another action"""
        for row in range(self.mappings_table.rowCount()):
            if row == current_row:
                continue  # Skip the current row
                
            # Check both current keys and new keys
            current_item = self.mappings_table.item(row, 1)
            if current_item and current_item.text() == key_combination:
                return True
                
            # Check if there's a key capture widget for this row
            if row < len(self.key_capture_widgets):
                widget_key = self.key_capture_widgets[row].text()
                if widget_key == key_combination:
                    return True
                    
        return False
            
    def on_key_captured(self, row, key_combination):
        """Handle key combination captured from custom widget"""
        # Check for duplicate keys
        if self._is_duplicate_key(key_combination, row):
            # Highlight the widget with error styling
            if row < len(self.key_capture_widgets):
                self.key_capture_widgets[row].setStyleSheet("""
                    QLineEdit {
                        background-color: #374151;
                        color: #ffffff;
                        font-size: 12px;
                        min-height: 25px;
                        border: 2px solid #dc2626;
                    }
                    QLineEdit:focus {
                        border-color: #dc2626;
                    }
                """)
                
            QMessageBox.warning(
                self, 
                "Duplicate Key", 
                f"The key '{key_combination}' is already assigned to another action. Please choose a different key."
            )
            # Reset the widget to its previous value
            if row < len(self.key_capture_widgets):
                previous_key = self.mappings_table.item(row, 1).text()
                self.key_capture_widgets[row].setText(previous_key)
                # Reset styling
                self.key_capture_widgets[row].setStyleSheet("""
                    QLineEdit {
                        background-color: #374151;
                        color: #ffffff;
                        font-size: 12px;
                        min-height: 25px;
                    }
                    QLineEdit:focus {
                        border-color: #3b82f6;
                    }
                """)
            return
            
        # Update the current key column to show the change
        current_item = self.mappings_table.item(row, 1)
        if current_item:
            current_item.setText(key_combination)
            
    def on_cell_changed(self, row, column):
        """Handle cell changes in the table"""
        if column == 2:  # New key column
            item = self.mappings_table.item(row, column)
            if item:
                key_text = item.text().strip()
                if key_text:
                    # Validate the key sequence
                    try:
                        QKeySequence(key_text)
                        # Update the current key column to show the change
                        current_item = self.mappings_table.item(row, 1)
                        if current_item:
                            current_item.setText(key_text)
                    except:
                        # Invalid key sequence, revert
                        item.setText(self.mappings_table.item(row, 1).text())
                        QMessageBox.warning(self, "Invalid Key", f"'{key_text}' is not a valid key sequence.")
                        
    def reset_to_defaults(self):
        """Reset all mappings to default values"""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all key mappings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to default keys
            actions = [
                ("Home Possession Toggle", "1"),
                ("Away Possession Toggle", "2"),
                ("Start Timer", "S"),
                ("Stop Timer", "T"),
                ("Reset Match", "r"),
                ("Home Goal +", "H"),
                ("Away Goal +", "A"),
                ("Home Goal -", "Shift+H"),
                ("Away Goal -", "Shift+A"),
            ]
            
            for row, (action, default_key) in enumerate(actions):
                current_item = self.mappings_table.item(row, 1)
                if current_item:
                    current_item.setText(default_key)
                # Update the key capture widget
                if row < len(self.key_capture_widgets):
                    self.key_capture_widgets[row].setText(default_key)
                    
    def apply_mappings(self):
        """Apply the new key mappings"""
        new_mappings = {}
        used_keys = set()
        
        # First pass: collect all keys and check for duplicates
        for row in range(self.mappings_table.rowCount()):
            action_item = self.mappings_table.item(row, 0)
            
            if action_item:
                action = action_item.text()
                # Get the key from the custom widget
                if row < len(self.key_capture_widgets):
                    new_key = self.key_capture_widgets[row].text().strip()
                    if new_key:
                        if new_key in used_keys:
                            QMessageBox.warning(
                                self, 
                                "Duplicate Keys", 
                                f"The key '{new_key}' is assigned to multiple actions. Please ensure each action has a unique key."
                            )
                            return
                        used_keys.add(new_key)
                        new_mappings[action] = new_key
                    
        # Emit signal with new mappings
        self.key_mapping_changed.emit(new_mappings)
        
        QMessageBox.information(self, "Success", "Key mappings have been updated successfully!")
        self.accept()
        
    def get_mappings(self):
        """Get the current mappings from the dialog"""
        mappings = {}
        for row in range(self.mappings_table.rowCount()):
            action_item = self.mappings_table.item(row, 0)
            
            if action_item:
                action = action_item.text()
                # Get the key from the custom widget
                if row < len(self.key_capture_widgets):
                    new_key = self.key_capture_widgets[row].text().strip()
                    if new_key:
                        mappings[action] = new_key
        return mappings
