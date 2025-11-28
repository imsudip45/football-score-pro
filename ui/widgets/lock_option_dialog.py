"""
Lock Option Dialog - Choose between Reset Match Lock and Master Lock
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class LockOptionDialog(QDialog):
    """Dialog for choosing lock type"""
    
    reset_lock_selected = Signal()
    master_lock_selected = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the lock option dialog UI"""
        self.setWindowTitle("Select Lock Type")
        self.setModal(True)
        self.setFixedSize(420, 320)
        
        # Set window flags to make it a proper dialog
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #0f172a);
                border: 1px solid #334155;
                border-radius: 16px;
            }
            QLabel {
                color: #e5e7eb;
            }
            QPushButton {
                border-radius: 10px;
                font-weight: bold;
                min-height: 50px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 28, 28, 28)
        
        # Title label
        title_label = QLabel("Choose Lock Type")
        title_label.setFont(QFont("Verdana", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("padding: 6px; font-size: 18px;")
        layout.addWidget(title_label)
        
        # Description label
        desc_label = QLabel("Select which type of lock you want to apply:")
        desc_label.setFont(QFont("Verdana", 10))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #94a3b8; padding: 4px;")
        layout.addWidget(desc_label)
        
        # Reset Match Lock button
        reset_lock_button = QPushButton("Set Reset Match Lock")
        reset_lock_button.setFont(QFont("Verdana", 11, QFont.Weight.Bold))
        reset_lock_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fbbf24, stop:1 #f59e0b);
                color: #0f172a;
                border: 1px solid #f59e0b;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fde68a, stop:1 #fbbf24);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f59e0b, stop:1 #d97706);
                color: white;
            }
        """)
        reset_lock_button.clicked.connect(self.on_reset_lock_clicked)
        layout.addWidget(reset_lock_button)
        
        # Master Lock button
        master_lock_button = QPushButton("Master Lock")
        master_lock_button.setFont(QFont("Verdana", 11, QFont.Weight.Bold))
        master_lock_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f87171, stop:1 #ef4444);
                color: #0f172a;
                border: 1px solid #ef4444;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fecaca, stop:1 #f87171);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
                color: white;
            }
        """)
        master_lock_button.clicked.connect(self.on_master_lock_clicked)
        layout.addWidget(master_lock_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        cancel_button.setMinimumHeight(46)
        cancel_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #e2e8f0;
                border: 1px solid #475569;
            }
            QPushButton:hover {
                background: rgba(148, 163, 184, 0.2);
            }
            QPushButton:pressed {
                background: rgba(148, 163, 184, 0.35);
            }
        """)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)
    
    def on_reset_lock_clicked(self):
        """Handle reset lock button click"""
        self.reset_lock_selected.emit()
        self.accept()
    
    def on_master_lock_clicked(self):
        """Handle master lock button click"""
        self.master_lock_selected.emit()
        self.accept()
