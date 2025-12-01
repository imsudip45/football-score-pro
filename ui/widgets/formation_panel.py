"""
Formation Panel Widget for Football Score Pro 2.0
Panel for formation selection and team data source
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
class FormationPanel(QWidget):
    """Panel for formation selection and team data source"""

    data_changed = Signal()

    def __init__(self, team_name: str, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.team_a_radio = None
        self.team_b_radio = None
        self.radio_group = None
        self._ignore_toggle = False
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the formation panel UI"""
        frame = QFrame()
        frame.setStyleSheet(self.get_frame_style())

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 5, 10, 5)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)

        self.team_a_radio = QRadioButton("Team A Data")
        self.team_a_radio.setChecked(self.team_name == "Home Team")
        self.team_a_radio.setStyleSheet(self.get_radio_button_style())
        self.team_a_radio.setEnabled(True)
        self.radio_group.addButton(self.team_a_radio)

        self.team_a_formation_label = QLabel("Select Formation")
        self.team_a_formation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team_a_formation_label.setStyleSheet(self.get_formation_label_style())
        self.team_a_formation_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._team_a_label_min_width = max(
            self.team_a_formation_label.sizeHint().width(), 140
        )
        self.team_a_formation_label.setMinimumWidth(self._team_a_label_min_width)
        self.team_a_formation_label.setFixedWidth(self._team_a_label_min_width)

        self.team_b_radio = QRadioButton("Team B Data")
        self.team_b_radio.setChecked(self.team_name == "Away Team")
        self.team_b_radio.setStyleSheet(self.get_radio_button_style())
        self.team_b_radio.setEnabled(True)
        self.radio_group.addButton(self.team_b_radio)

        self.team_b_formation_label = QLabel("Select Formation")
        self.team_b_formation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team_b_formation_label.setStyleSheet(self.get_formation_label_style())
        self.team_b_formation_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._team_b_label_min_width = max(
            self.team_b_formation_label.sizeHint().width(), 140
        )
        self.team_b_formation_label.setMinimumWidth(self._team_b_label_min_width)
        self.team_b_formation_label.setFixedWidth(self._team_b_label_min_width)

        grid_layout.addWidget(self.team_a_radio, 0, 0)
        grid_layout.addWidget(self.team_a_formation_label, 0, 1)
        grid_layout.addWidget(self.team_b_radio, 0, 2)
        grid_layout.addWidget(self.team_b_formation_label, 0, 3)

        layout.addLayout(grid_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def connect_signals(self):
        """Connect signals for radio buttons"""
        if self.team_a_radio:
            self.team_a_radio.toggled.connect(self.on_data_source_changed)
        if self.team_b_radio:
            self.team_b_radio.toggled.connect(self.on_data_source_changed)

    def update_display(self, team_data: dict):
        """Update display with team data"""
        try:
            self._ignore_toggle = True
            data_source = team_data.get("data_source", "Team A")
            if data_source == "Team A":
                if self.team_a_radio and not self.team_a_radio.isChecked():
                    self.team_a_radio.setChecked(True)
            else:
                if self.team_b_radio and not self.team_b_radio.isChecked():
                    self.team_b_radio.setChecked(True)
            self._ignore_toggle = False
        except Exception:
            self._ignore_toggle = False

    def update_radio_selection(self, data_source: str):
        """Update radio button selection based on data source"""
        try:
            self._ignore_toggle = True
            if data_source == "Team A":
                if self.team_a_radio and not self.team_a_radio.isChecked():
                    self.team_a_radio.setChecked(True)
            else:
                if self.team_b_radio and not self.team_b_radio.isChecked():
                    self.team_b_radio.setChecked(True)
            self._ignore_toggle = False
        except Exception:
            self._ignore_toggle = False

    def update_team_data(self, team_data: dict):
        """Update team object with current panel data"""
        try:
            if self.team_a_radio and self.team_a_radio.isChecked():
                team_data["data_source"] = "Team A"
            elif self.team_b_radio and self.team_b_radio.isChecked():
                team_data["data_source"] = "Team B"
        except Exception as e:
            print(f"Error updating team data from formation panel: {e}")

    def on_data_source_changed(self, checked: bool):
        """Handle data source radio button changes"""
        if not checked:
            return
        if self._ignore_toggle:
            return

        # Determine which data source was selected
        if self.team_a_radio and self.team_a_radio.isChecked():
            data_source = "Team A"
        elif self.team_b_radio and self.team_b_radio.isChecked():
            data_source = "Team B"
        else:
            return

        # Emit signal with data source information
        self.data_changed.emit()

        # Notify parent to switch data source
        parent = self.parent()
        if parent is not None and hasattr(parent, "switch_data_source"):
            parent.switch_data_source(data_source)  # type: ignore[union-attr]

    def set_data_source_without_emit(self, data_source: str):
        """Set data source without emitting signal (for syncing)"""
        try:
            self._ignore_toggle = True
            if self.team_a_radio:
                self.team_a_radio.blockSignals(True)
            if self.team_b_radio:
                self.team_b_radio.blockSignals(True)
            if data_source == "Team A":
                if self.team_a_radio:
                    self.team_a_radio.setChecked(True)
                if self.team_b_radio:
                    self.team_b_radio.setChecked(False)
            elif data_source == "Team B":
                if self.team_b_radio:
                    self.team_b_radio.setChecked(True)
                if self.team_a_radio:
                    self.team_a_radio.setChecked(False)
        finally:
            if self.team_a_radio:
                self.team_a_radio.blockSignals(False)
            if self.team_b_radio:
                self.team_b_radio.blockSignals(False)
            self._ignore_toggle = False

    def update_team_a_formation(self, formation: str, maintain_width: bool = False):
        """Update only Team A formation label"""
        try:
            if self.team_a_formation_label:
                self.team_a_formation_label.setText(formation)
                hint = self.team_a_formation_label.sizeHint().width()
                if maintain_width and hasattr(self, "_team_a_label_min_width"):
                    self.team_a_formation_label.setFixedWidth(
                        self._team_a_label_min_width
                    )
                else:
                    width = max(hint, getattr(self, "_team_a_label_min_width", 140))
                    self._team_a_label_min_width = width
                    self.team_a_formation_label.setFixedWidth(width)
        except Exception as e:
            print(f"Error updating Team A formation label: {e}")

    def update_team_b_formation(self, formation: str, maintain_width: bool = False):
        """Update only Team B formation label"""
        try:
            if self.team_b_formation_label:
                self.team_b_formation_label.setText(formation)
                hint = self.team_b_formation_label.sizeHint().width()
                if maintain_width and hasattr(self, "_team_b_label_min_width"):
                    self.team_b_formation_label.setFixedWidth(
                        self._team_b_label_min_width
                    )
                else:
                    width = max(hint, getattr(self, "_team_b_label_min_width", 140))
                    self._team_b_label_min_width = width
                    self.team_b_formation_label.setFixedWidth(width)
        except Exception as e:
            print(f"Error updating Team B formation label: {e}")

    def update_radio_texts(self, team_a_short_name: str, team_b_short_name: str):
        """Update both radio button labels with team short names."""
        try:
            if self.team_a_radio:
                self.team_a_radio.setText(f"{team_a_short_name} Data")
            if self.team_b_radio:
                self.team_b_radio.setText(f"{team_b_short_name} Data")
        except Exception as e:
            print(f"Error updating radio texts: {e}")

    def get_selected_team_type(self) -> str:
        """Get the currently selected team key: "A" or "B"."""
        try:
            if self.team_a_radio and self.team_a_radio.isChecked():
                return "A"
            elif self.team_b_radio and self.team_b_radio.isChecked():
                return "B"
            return "A"
        except Exception as e:
            print(f"Error getting selected team type: {e}")
            return "A"

    def get_current_data_source(self) -> str:
        """Get the currently selected data source"""
        try:
            if self.team_a_radio and self.team_a_radio.isChecked():
                return "Team A"
            elif self.team_b_radio and self.team_b_radio.isChecked():
                return "Team B"
            return "Team A"
        except Exception as e:
            print(f"Error getting current data source: {e}")
            return "Team A"

    def update_radio_labels(self, team_a_name: str, team_b_name: str):
        """Update radio button labels with actual team names"""
        try:
            if self.team_a_radio:
                self.team_a_radio.setText(f"{team_a_name} Data")
            if self.team_b_radio:
                self.team_b_radio.setText(f"{team_b_name} Data")
        except Exception as e:
            print(f"Error updating radio labels: {e}")

    def get_frame_style(self) -> str:
        """Get frame style"""
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #374151;
                border-radius: 8px;
            }
        """

    def get_radio_button_style(self) -> str:
        """Get radio button style"""
        return """
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #6b7280;
                background: #1f2937;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #10b981;
                background: #10b981;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #9ca3af;
            }
        """

    def get_formation_label_style(self) -> str:
        """Get formation label style"""
        return """
            QLabel {
                background: rgba(37, 37, 37, 0.8);
                border: 2px solid #059669;
                color: #059669;
                padding: 8px 0px;

                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
        """
