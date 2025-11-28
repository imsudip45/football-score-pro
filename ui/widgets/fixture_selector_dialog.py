"""
Fixture Selector Dialog for selecting from multiple fixtures
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FixtureSelectorDialog(QDialog):
    """Dialog for selecting a fixture from multiple available fixtures"""
    
    # Signal emitted when a fixture is selected
    fixture_selected = Signal(dict)
    
    def __init__(self, fixtures_data: list, parent_data=None, parent=None):
        super().__init__(parent)
        self.fixtures_data = fixtures_data
        self.parent_data = parent_data  # Store parent data with available officials/commentators/hosts
        self.selected_fixture = None
        self.setup_ui()
        self.populate_fixtures()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Select Fixture")
        self.setModal(True)
        self.resize(1100, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Select a Fixture to Load")
        title_label.setFont(QFont("Verdana", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Fixtures table
        self.fixtures_table = QTableWidget()
        self.fixtures_table.setColumnCount(8)
        self.fixtures_table.setHorizontalHeaderLabels([
            "Match #", "Date", "Time", "Home Team", "Away Team", "Venue", "Round", "Status"
        ])
        
        # Configure table
        self.fixtures_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.fixtures_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fixtures_table.setAlternatingRowColors(True)
        self.fixtures_table.setSortingEnabled(True)
        self.fixtures_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Prevent inline edits
        
        # Set column widths
        header = self.fixtures_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Match #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Date
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Time
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Home Team
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Away Team
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Venue
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Round
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Status
        
        self.fixtures_table.setColumnWidth(0, 60)   # Match #
        self.fixtures_table.setColumnWidth(1, 100)  # Date
        self.fixtures_table.setColumnWidth(2, 80)    # Time
        self.fixtures_table.setColumnWidth(6, 100)  # Round
        self.fixtures_table.setColumnWidth(7, 80)    # Status
        
        layout.addWidget(self.fixtures_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select Fixture")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self.select_fixture)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Connect table selection
        self.fixtures_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                padding: 10px;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                gridline-color: #4a4a4a;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4a4a4a;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #4a4a4a;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: 1px solid #357abd;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #666666;
                border: 1px solid #888888;
            }
        """)
    
    def populate_fixtures(self):
        """Populate the fixtures table with data"""
        try:
            self.fixtures_table.setRowCount(len(self.fixtures_data))
            
            for row, fixture in enumerate(self.fixtures_data):
                # Match number
                match_num = fixture.get('match_number', row + 1)
                self.fixtures_table.setItem(row, 0, QTableWidgetItem(str(match_num)))
                
                # Date
                date = fixture.get('date', 'N/A')
                self.fixtures_table.setItem(row, 1, QTableWidgetItem(date))
                
                # Time
                time = fixture.get('time', 'N/A')
                self.fixtures_table.setItem(row, 2, QTableWidgetItem(time))
                
                # Home team
                teams = fixture.get('teams', [])
                home_team = teams[0] if len(teams) > 0 else {}
                home_name = home_team.get('name', home_team.get('full_name', 'Unknown'))
                self.fixtures_table.setItem(row, 3, QTableWidgetItem(home_name))
                
                # Away team
                away_team = teams[1] if len(teams) > 1 else {}
                away_name = away_team.get('name', away_team.get('full_name', 'Unknown'))
                self.fixtures_table.setItem(row, 4, QTableWidgetItem(away_name))
                
                # Venue
                venue = fixture.get('venue', 'N/A')
                self.fixtures_table.setItem(row, 5, QTableWidgetItem(venue))
                
                # Round
                round_name = fixture.get('round', 'N/A')
                self.fixtures_table.setItem(row, 6, QTableWidgetItem(round_name))
                
                # Status
                status = fixture.get('status', 'scheduled')
                status_item = QTableWidgetItem(status.title())
                if status == 'scheduled':
                    status_item.setBackground(Qt.GlobalColor.blue)
                elif status == 'live':
                    status_item.setBackground(Qt.GlobalColor.green)
                elif status == 'finished':
                    status_item.setBackground(Qt.GlobalColor.gray)
                self.fixtures_table.setItem(row, 7, status_item)
                
                # Store fixture data in the first column for easy access
                self.fixtures_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, fixture)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to populate fixtures: {str(e)}")
    
    def on_selection_changed(self):
        """Handle table selection change"""
        selected_rows = self.fixtures_table.selectionModel().selectedRows()
        self.select_button.setEnabled(len(selected_rows) > 0)
    
    def select_fixture(self):
        """Select the currently selected fixture"""
        try:
            selected_rows = self.fixtures_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "Please select a fixture first.")
                return
            
            row = selected_rows[0].row()
            fixture_item = self.fixtures_table.item(row, 0)
            fixture_data = fixture_item.data(Qt.ItemDataRole.UserRole)
            
            if fixture_data:
                self.selected_fixture = fixture_data
                # Attach parent data (available officials, commentators, hosts) to fixture
                if self.parent_data:
                    fixture_data['_parent_data'] = self.parent_data
                self.fixture_selected.emit(fixture_data)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No fixture data found for selected row.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select fixture: {str(e)}")
    
    def get_selected_fixture(self):
        """Get the selected fixture data"""
        return self.selected_fixture

