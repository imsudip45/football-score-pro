"""
Info Panel Widget for FSP 2.0
Displays team information and player selection count
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from .modern_components import ModernButton, ModernLabel


class InfoPanel(QWidget):
    """Panel displaying team information and statistics"""

    def __init__(self, team_name: str, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.team_type = "Home" if "Home" in team_name else "Away" if "Away" in team_name else "Team"
        
        self.team_name_label = None
        self.selected_label = None
        self.reset_button = None
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the info panel UI"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827); }
        """)

        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # Team name label (moved to where Manager label was)
        
        self.team_name_label = QLabel(f"Team Not Set")
        
        self.team_name_label.setAlignment(Qt.AlignCenter)
        self.team_name_label.setStyleSheet(self.get_info_label_style())
        layout.addWidget(self.team_name_label)
        
        # Manager label removed - now displayed on the field in ContentPanel

        layout.addStretch()

        # Selected count label
        self.selected_label = ModernLabel("Selected: 0/11", "error")
        self.selected_label.setObjectName(f"selected_label_{self.team_name.lower().replace(' ', '_')}")
        self.selected_label.setStyleSheet(self.get_selected_count_style())
        layout.addWidget(self.selected_label)

        # Reset button
        self.reset_button = ModernButton(f"Reset {self.team_name}", "danger")
        layout.addWidget(self.reset_button)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def update_display(self, team_data: dict):
        """Update display with team data"""
        try:
            # Manager label is now in ContentPanel, not here
            
            if self.team_name_label:
                # Try different possible keys for team name
                team_text = (team_data.get('team_fullname') or 
                            team_data.get('full_name') or 
                            team_data.get('name') or 
                            team_data.get('team_name') or 
                            'Not Set')
                self.team_name_label.setText(f"{team_text}")
                # Reapply stylesheet to ensure padding is respected after text change
                self.team_name_label.setStyleSheet(self.get_info_label_style())
            
            # Update selected count
            selected_count = team_data.get('selected_count', 0)
            self.update_selected_count(selected_count)
            
        except Exception as e:
            print(f"Error updating info panel display for {self.team_name}: {e}")

    def update_team_data(self, team_data: dict):
        """Update team data with current panel data"""
        try:
            if self.team_name_label:
                label_text = self.team_name_label.text()
                if ": " in label_text:
                    team_name_part = label_text.split(": ", 1)[1]
                    if team_name_part != "Not Set":
                        team_data['team_fullname'] = team_name_part
            
            # Manager label is now in ContentPanel, not here
        except Exception as e:
            print(f"Error updating team data from info panel: {e}")

    def update_selected_count(self, count: int):
        """Update the selected players count display"""
        try:
            if self.selected_label:
                max_players = 11
                self.selected_label.setText(f"Selected: {count}/{max_players}")
                
                # Update label style based on count
                if count == max_players:
                    self.selected_label.setStyleSheet(self.get_selected_count_style("success"))
                else:
                    # Show error color for 0, less than 11, or more than 11
                    self.selected_label.setStyleSheet(self.get_selected_count_style("error"))
        except Exception as e:
            print(f"Error updating selected count for {self.team_name}: {e}")

    def connect_reset_button(self, callback):
        """Connect reset button to callback function"""
        if self.reset_button:
            self.reset_button.clicked.connect(callback)

    def get_info_label_style(self) -> str:
        """Get info label stylesheet"""
        return """
            QLabel {
                color: rgba(229, 231, 235, 0.7);
                font-weight: 600;
                font-size: 14px;
                padding: 8px 8px;
                border: none;
            }
        """

    def get_selected_count_style(self, label_type: str = "error") -> str:
        """Get selected count label stylesheet"""
        colors = {
            "success": "#10b981",
            "error": "#ef4444"
        }
        backgrounds = {
            "success": "rgba(16, 185, 129, 0.1)",  # Green background
            "error": "rgba(239, 68, 68, 0.1)"       # Red background
        }
        color = colors.get(label_type, "#ef4444")
        background = backgrounds.get(label_type, "rgba(239, 68, 68, 0.1)")
        
        return f"""
            QLabel {{
                color: {color};
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
                background: {background};
                border: 2px solid {color};
                border-radius: 8px;
                min-width: 120px;
                text-align: center;
            }}
        """

