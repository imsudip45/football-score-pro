"""
Lock Overlay Widget - Shows "LOCKED" text over darkened content
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget


class LockOverlay(QWidget):
    """Overlay widget that shows LOCKED text over darkened content"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the lock overlay UI"""
        # Make overlay fill parent and be on top
        self.setAutoFillBackground(True)

        # Completely opaque black background
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(0, 0, 0);
            }
        """)

        # Create LOCKED label with semi-transparent blurry background
        self.locked_label = QLabel("LOCKED", self)
        self.locked_label.setFont(QFont("Verdana", 60, QFont.Weight.Bold))
        self.locked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.locked_label.setStyleSheet("""
            QLabel {
                color: #dc2626;
                background: rgba(255, 255, 255, 0.3);
                padding: 30px 40px;
                border: 1px solid #dc2626;
                border-radius: 20px;
            }
        """)

        # Initially hidden
        self.hide()

    def resizeEvent(self, event):
        """Handle resize to keep overlay covering parent and center label"""
        super().resizeEvent(event)
        parent = self.parent()
        if parent is not None and hasattr(parent, "rect"):
            # Make overlay cover entire parent
            self.setGeometry(parent.rect())
            # Center the label - increased size
            label_width = 600
            label_height = 200
            x = (self.width() - label_width) // 2
            y = (self.height() - label_height) // 2
            self.locked_label.setGeometry(x, y, label_width, label_height)

    def showEvent(self, event):
        """Ensure overlay is on top when shown and center label"""
        super().showEvent(event)
        self.raise_()
        parent = self.parent()
        if parent is not None and hasattr(parent, "rect"):
            # Make overlay cover entire parent
            self.setGeometry(parent.rect())
            # Center the label - increased size
            label_width = 600
            label_height = 200
            x = (self.width() - label_width) // 2
            y = (self.height() - label_height) // 2
            self.locked_label.setGeometry(x, y, label_width, label_height)
