"""
Fixture Loader Dialog for loading match data from JSON files or API URLs
"""

import json
import requests
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QRadioButton, QLineEdit, QPushButton, QFileDialog, QTextEdit,
    QLabel, QMessageBox, QProgressDialog, QButtonGroup, QStackedWidget,
    QFormLayout, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FixtureLoaderDialog(QDialog):
    """Dialog for loading fixture data from JSON file or API URL"""
    
    # Signal emitted when fixture data is loaded successfully
    fixture_loaded = Signal(dict)
    
    def __init__(self, backend_service=None, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service
        self.fixture_data = None
        self.setup_ui()
        self.setup_styling()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Load Fixture")
        self.setModal(True)
        self.resize(800, 800)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title_label = QLabel("Load Fixture Data")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setContentsMargins(0, 0, 0, 6)
        layout.addWidget(title_label)
        
        # Source selection (compact header row)
        source_row = QHBoxLayout()
        source_row.setSpacing(12)
        source_label = QLabel("Data Source:")
        source_label.setObjectName("sectionLabel")
        self.file_radio = QRadioButton("Load from JSON File")
        self.api_radio = QRadioButton("Load from API URL")
        self.file_radio.setChecked(True)
        self.source_group = QButtonGroup()
        self.source_group.addButton(self.file_radio, 0)
        self.source_group.addButton(self.api_radio, 1)
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        source_row.addWidget(self.file_radio)
        source_row.addWidget(self.api_radio)
        source_row.addStretch(2)
        layout.addLayout(source_row)

        # Stacked panels for inputs (no groupbox titles → no extra top gap)
        self.input_stack = QStackedWidget()

        # File page
        file_page = QWidget()
        file_page_layout = QFormLayout(file_page)
        file_page_layout.setContentsMargins(8, 8, 8, 8)
        file_page_layout.setSpacing(8)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("JSON file path...")
        self.file_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse")
        self.browse_button.setFixedWidth(90)
        self.browse_button.clicked.connect(self.browse_file)
        # Compose the row with a horizontal layout (no wrapper widget needed)
        file_row_layout = QHBoxLayout()
        file_row_layout.setContentsMargins(0, 0, 0, 0)
        file_row_layout.setSpacing(15)
        file_row_layout.addWidget(self.file_path_edit, 1)
        file_row_layout.addWidget(self.browse_button)
        # Put the label above the input row, centered with bottom gap
        label_choose_file = QLabel("Choose a JSON file to load:")
        label_choose_file.setAlignment(Qt.AlignLeft)
        label_choose_file.setContentsMargins(0, 0, 0, 15)  # bottom gap
        file_page_layout.addRow(label_choose_file)
        file_page_layout.addRow(file_row_layout)

        file_frame = QFrame()
        file_frame.setObjectName("sectionFrame")
        file_frame_l = QVBoxLayout(file_frame)
        file_frame_l.setContentsMargins(10, 10, 10, 10)
        file_frame_l.addWidget(file_page)

        # API page
        api_page = QWidget()
        api_form = QFormLayout(api_page)
        api_form.setContentsMargins(8, 8, 8, 8)
        api_form.setSpacing(10)
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://api.example.com/fixture/123")
        self.headers_edit = QTextEdit()
        self.headers_edit.setPlaceholderText('{"Authorization": "Bearer your_token", "Content-Type": "application/json"}')
        self.headers_edit.setMaximumHeight(80)
        api_form.addRow("API URL:", self.api_url_edit)
        api_form.addRow("Headers (optional):", self.headers_edit)

        api_frame = QFrame()
        api_frame.setObjectName("sectionFrame")
        api_frame_l = QVBoxLayout(api_frame)
        api_frame_l.setContentsMargins(10, 10, 10, 10)
        api_frame_l.addWidget(api_page)

        self.input_stack.addWidget(file_frame)  # 0
        self.input_stack.addWidget(api_frame)   # 1
        layout.addWidget(self.input_stack)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.load_button = QPushButton("Load Fixture")
        self.load_button.clicked.connect(self.load_fixture)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect radio button changes
        self.file_radio.toggled.connect(self.on_source_changed)
        self.api_radio.toggled.connect(self.on_source_changed)
        
        # Set initial visibility
        self.on_source_changed()

        # Force initial polish/layout so spacing matches post-toggle behaviour
        try:
            for panel in (self.input_stack.widget(0), self.input_stack.widget(1)):
                if panel:
                    st = panel.style()
                    st.unpolish(panel)
                    st.polish(panel)
                    panel.updateGeometry()
        except Exception:
            pass
        if self.layout():
            self.layout().activate()
        self.adjustSize()
        
    def setup_styling(self):
        """Apply modern styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1f2937;
                color: #ffffff;
            }
            QLabel#sectionLabel {
                color: #9ca3af;
                font-weight: 600;
            }
            QFrame#sectionFrame {
                border: 2px solid #374151;
                border-radius: 8px;
                background-color: #111827;
            }
            QRadioButton {
                color: #ffffff;
                font-size: 14px;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator::unchecked {
                border: 2px solid #6b7280;
                border-radius: 8px;
                background-color: transparent;
            }
            QRadioButton::indicator::checked {
                border: 2px solid #3b82f6;
                border-radius: 8px;
                background-color: #3b82f6;
            }
            QLineEdit, QTextEdit {
                background-color: #374151;
                border: 2px solid #4b5563;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3b82f6;
            }
            QPushButton {
                background-color: #374151;
                border: 2px solid #4b5563;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border-color: #6b7280;
            }
            QPushButton:pressed {
                background-color: #6b7280;
            }
            QPushButton:disabled {
                background-color: #1f2937;
                border-color: #374151;
                color: #6b7280;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
        """)
        
    def on_source_changed(self):
        """Handle source selection changes"""
        is_file = self.file_radio.isChecked()
        if hasattr(self, 'input_stack'):
            self.input_stack.setCurrentIndex(0 if is_file else 1)
        self.fixture_data = None
        
    def browse_file(self):
        """Open file browser to select JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Fixture JSON File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            
    def load_fixture(self):
        """Load the fixture data and close dialog"""
        data = None
        try:
            if self.file_radio.isChecked():
                file_path = self.file_path_edit.text().strip()
                if not file_path:
                    QMessageBox.warning(self, "Warning", "Please select a JSON file first.")
                    return
                if not Path(file_path).exists():
                    QMessageBox.warning(self, "Error", "Selected file does not exist.")
                    return
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                api_url = self.api_url_edit.text().strip()
                if not api_url:
                    QMessageBox.warning(self, "Warning", "Please enter an API URL.")
                    return

                headers = {}
                headers_text = self.headers_edit.toPlainText().strip()
                if headers_text:
                    try:
                        headers = json.loads(headers_text)
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "Error", "Invalid JSON format in headers.")
                        return

                progress = QProgressDialog("Fetching data from API...", "Cancel", 0, 0, self)
                progress.setWindowTitle("Loading Data")
                progress.setModal(True)
                progress.show()

                try:
                    response = requests.get(api_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                finally:
                    progress.close()

            self.fixture_data = data

            if isinstance(self.fixture_data, dict) and 'fixtures' in self.fixture_data:
                fixtures_list = self.fixture_data.get('fixtures', [])
                if len(fixtures_list) > 1:
                    from .fixture_selector_dialog import FixtureSelectorDialog
                    selector_dialog = FixtureSelectorDialog(fixtures_list, self.fixture_data, self)
                    selector_dialog.fixture_selected.connect(self.on_fixture_selected)
                    selector_dialog.exec()
                    return
                elif len(fixtures_list) == 1:
                    fixture = fixtures_list[0]
                    fixture['_parent_data'] = self.fixture_data
                    self.fixture_loaded.emit(fixture)
                    self.accept()
                    return
            elif isinstance(self.fixture_data, list) and len(self.fixture_data) > 1:
                from .fixture_selector_dialog import FixtureSelectorDialog
                selector_dialog = FixtureSelectorDialog(self.fixture_data, None, self)
                selector_dialog.fixture_selected.connect(self.on_fixture_selected)
                selector_dialog.exec()
                return

            self.fixture_loaded.emit(self.fixture_data)
            self.accept()

        except requests.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to fetch data from API:\n{str(e)}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON data:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")
    
    def on_fixture_selected(self, fixture_data):
        """Handle fixture selection from selector dialog"""
        try:
            self.fixture_loaded.emit(fixture_data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load selected fixture: {str(e)}")
            
    def get_fixture_data(self):
        """Get the loaded fixture data"""
        return self.fixture_data
