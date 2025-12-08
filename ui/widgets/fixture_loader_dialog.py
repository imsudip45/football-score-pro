"""
Fixture Loader Dialog for loading match data from JSON files, API URLs, or Backend
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QRadioButton, QLineEdit, QPushButton, QFileDialog, QTextEdit,
    QLabel, QMessageBox, QProgressDialog, QButtonGroup, QStackedWidget,
    QFormLayout, QFrame, QWidget, QListWidget, QListWidgetItem, QComboBox,
    QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import backend API
try:
    from ..backend_api import get_api
except ImportError:
    get_api = None


class FixtureLoaderDialog(QDialog):
    """Dialog for loading fixture data from JSON file or API URL"""
    
    # Signal emitted when fixture data is loaded successfully
    fixture_loaded = Signal(dict)
    
    def __init__(self, backend_service=None, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service
        self.fixture_data = None
        self._all_fixtures = []
        self._fixtures: Dict[str, Dict[str, Any]] = {}
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
        self.backend_radio = QRadioButton("Load from Backend")
        self.file_radio = QRadioButton("Load from JSON File")
        self.api_radio = QRadioButton("Load from API URL")
        self.backend_radio.setChecked(True)  # Default to backend
        self.source_group = QButtonGroup()
        self.source_group.addButton(self.backend_radio, 0)
        self.source_group.addButton(self.file_radio, 1)
        self.source_group.addButton(self.api_radio, 2)
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        source_row.addWidget(self.backend_radio)
        source_row.addWidget(self.file_radio)
        source_row.addWidget(self.api_radio)
        source_row.addStretch(2)
        layout.addLayout(source_row)

        # Stacked panels for inputs (no groupbox titles → no extra top gap)
        self.input_stack = QStackedWidget()

        # Backend page (Load from local backend / cloud)
        backend_page = QWidget()
        backend_layout = QVBoxLayout(backend_page)
        backend_layout.setContentsMargins(8, 8, 8, 8)
        backend_layout.setSpacing(10)
        
        # Refresh button and status
        refresh_row = QHBoxLayout()
        self.refresh_backend_btn = QPushButton("🔄 Refresh Local Fixtures")
        self.refresh_backend_btn.clicked.connect(self.refresh_backend_fixtures)
        self.backend_status_label = QLabel("")
        self.backend_status_label.setStyleSheet("color: #9ca3af;")
        refresh_row.addWidget(self.refresh_backend_btn)
        refresh_row.addWidget(self.backend_status_label)
        refresh_row.addStretch()
        backend_layout.addLayout(refresh_row)
        
        # Tournament filter
        tournament_row = QHBoxLayout()
        tournament_row.addWidget(QLabel("Tournament:"))
        self.tournament_combo = QComboBox()
        self.tournament_combo.addItem("All Tournaments", None)
        self.tournament_combo.currentIndexChanged.connect(self.on_tournament_filter_changed)
        tournament_row.addWidget(self.tournament_combo, 1)
        backend_layout.addLayout(tournament_row)
        
        # Fixtures list
        fixtures_label = QLabel("Available Fixtures:")
        fixtures_label.setStyleSheet("font-weight: bold;")
        backend_layout.addWidget(fixtures_label)
        
        self.fixtures_list = QListWidget()
        self.fixtures_list.setMinimumHeight(200)
        self.fixtures_list.itemDoubleClicked.connect(self.on_fixture_double_clicked)
        self.fixtures_list.currentItemChanged.connect(self.on_fixture_selection_changed)
        backend_layout.addWidget(self.fixtures_list)
        
        # Selected fixture info
        self.selected_fixture_info = QLabel("Select a fixture to load")
        self.selected_fixture_info.setStyleSheet("color: #9ca3af; font-style: italic;")
        self.selected_fixture_info.setWordWrap(True)
        backend_layout.addWidget(self.selected_fixture_info)
        
        backend_frame = QFrame()
        backend_frame.setObjectName("sectionFrame")
        backend_frame_l = QVBoxLayout(backend_frame)
        backend_frame_l.setContentsMargins(10, 10, 10, 10)
        backend_frame_l.addWidget(backend_page)

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

        self.input_stack.addWidget(backend_frame)  # 0 - Backend
        self.input_stack.addWidget(file_frame)     # 1 - File
        self.input_stack.addWidget(api_frame)      # 2 - API
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
        self.backend_radio.toggled.connect(self.on_source_changed)
        self.file_radio.toggled.connect(self.on_source_changed)
        self.api_radio.toggled.connect(self.on_source_changed)
        
        # Set initial visibility
        self.on_source_changed()
        
        # Load local fixtures on startup
        self.load_backend_fixtures_on_startup()

        # Force initial polish/layout so spacing matches post-toggle behaviour
        try:
            for panel in (self.input_stack.widget(0), self.input_stack.widget(1), self.input_stack.widget(2)):
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
            QListWidget {
                background-color: #374151;
                border: 2px solid #4b5563;
                border-radius: 6px;
                color: #ffffff;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4b5563;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
            }
            QListWidget::item:hover {
                background-color: #4b5563;
            }
            QComboBox {
                background-color: #374151;
                border: 2px solid #4b5563;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #6b7280;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #374151;
                border: 2px solid #4b5563;
                color: #ffffff;
                selection-background-color: #3b82f6;
            }
        """)
        
    def on_source_changed(self):
        """Handle source selection changes"""
        if hasattr(self, 'input_stack'):
            if self.backend_radio.isChecked():
                self.input_stack.setCurrentIndex(0)
            elif self.file_radio.isChecked():
                self.input_stack.setCurrentIndex(1)
            else:
                self.input_stack.setCurrentIndex(2)
        self.fixture_data = None
    
    def load_backend_fixtures_on_startup(self):
        """Load fixtures from local backend on dialog startup"""
        try:
            if get_api is None:
                self.backend_status_label.setText("Backend API not available")
                return

            api = get_api()
            if not api.health_check():
                self.backend_status_label.setText("Backend offline - start server first")
                return

            # Load fixtures and populate filters
            self.refresh_fixtures_list(update_filters=True)
        except Exception as e:
            self.backend_status_label.setText(f"Error: {str(e)}")
    
    def _populate_tournament_filter(
        self, fixtures: List[Dict[str, Any]], selected_id: Optional[str]
    ) -> None:
        """Populate the tournament filter based on locally available fixtures."""
        self.tournament_combo.blockSignals(True)
        try:
            tournament_map: Dict[str, str] = {}
            has_orphan_fixtures = False

            for fixture in fixtures:
                tid = fixture.get("tournament_id")
                tournament = fixture.get("tournament") or {}
                if tid:
                    label = tournament.get("name") or tid
                    if tid not in tournament_map:
                        tournament_map[tid] = label
                else:
                    has_orphan_fixtures = True

            self.tournament_combo.clear()
            self.tournament_combo.addItem("All Tournaments", None)

            for tid, label in sorted(tournament_map.items(), key=lambda item: item[1]):
                self.tournament_combo.addItem(label, tid)

            if has_orphan_fixtures:
                self.tournament_combo.addItem("No Tournament", "__none__")

            valid_ids = set(tournament_map.keys())
            if has_orphan_fixtures:
                valid_ids.add("__none__")

            if selected_id not in valid_ids:
                selected_id = None

            if selected_id is None:
                self.tournament_combo.setCurrentIndex(0)
            else:
                matched_index = 0
                for idx in range(self.tournament_combo.count()):
                    if self.tournament_combo.itemData(idx) == selected_id:
                        matched_index = idx
                        break
                self.tournament_combo.setCurrentIndex(matched_index)
        finally:
            self.tournament_combo.blockSignals(False)

    def on_fixture_selection_changed(self, current, previous):
        """Update info panel when the selected fixture changes."""
        if current is None:
            self.selected_fixture_info.setText("Select a fixture to load")
            return

        fixture_id = current.data(Qt.UserRole)
        fixture = self._fixtures.get(fixture_id)
        if not fixture:
            self.selected_fixture_info.setText("Select a fixture to load")
            return

        home = fixture.get("home_team", {}) or {}
        away = fixture.get("away_team", {}) or {}
        tournament = fixture.get("tournament", {}) or {}

        home_name = (
            home.get("name") or home.get("short_name") or "Home"
        )
        away_name = (
            away.get("name") or away.get("short_name") or "Away"
        )
        header = f"{home_name} vs {away_name}"

        meta_parts: List[str] = []
        tournament_name = tournament.get("name")
        if tournament_name:
            meta_parts.append(tournament_name)

        scheduled = (
            fixture.get("scheduled_at")
            or fixture.get("scheduled_date")
            or ""
        )
        if scheduled:
            meta_parts.append(str(scheduled).replace("T", " "))

        venue = fixture.get("venue")
        if venue:
            meta_parts.append(venue)

        status = fixture.get("status")
        if status and status not in {"scheduled", None}:
            meta_parts.append(status.title())

        if meta_parts:
            header += "\n" + " • ".join(meta_parts)

        self.selected_fixture_info.setText(header)

    def refresh_backend_fixtures(self):
        """Refresh fixtures from local backend"""
        try:
            if get_api is None:
                QMessageBox.warning(self, "Error", "Backend API not available")
                return

            api = get_api()
            if not api.health_check():
                QMessageBox.warning(
                    self,
                    "Error",
                    "Backend is offline. Please start the server first.",
                )
                return

            current_id = self.tournament_combo.currentData()
            self.refresh_fixtures_list(
                tournament_id=current_id, update_filters=True
            )
            self.backend_status_label.setText("Refreshed from backend")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh: {str(e)}")
    
    def refresh_fixtures_list(self, tournament_id=None, update_filters=False):
        """Refresh the fixtures list from the local backend"""
        try:
            if get_api is None:
                return

            api = get_api()
            fixtures = api.get_fixtures() or []
            self._all_fixtures = fixtures
            self._fixtures = {
                f.get("id"): f for f in fixtures if f.get("id")
            }

            if update_filters:
                selected_id = tournament_id
                if selected_id is None:
                    selected_id = self.tournament_combo.currentData()
                self._populate_tournament_filter(fixtures, selected_id)
                tournament_id = self.tournament_combo.currentData()

            if tournament_id == "__none__":
                fixtures_to_show = [
                    f for f in fixtures if not f.get("tournament_id")
                ]
            elif tournament_id:
                fixtures_to_show = [
                    f for f in fixtures if f.get("tournament_id") == tournament_id
                ]
            else:
                fixtures_to_show = fixtures

            self.fixtures_list.clear()

            if fixtures_to_show:
                for fixture in fixtures_to_show:
                    fixture_id = fixture.get("id")
                    home = fixture.get("home_team", {}) or {}
                    away = fixture.get("away_team", {}) or {}
                    tournament = fixture.get("tournament", {}) or {}

                    home_name = (
                        home.get("name")
                        or home.get("short_name")
                        or "Home"
                    )
                    away_name = (
                        away.get("name")
                        or away.get("short_name")
                        or "Away"
                    )
                    venue = fixture.get("venue") or ""
                    scheduled = (
                        fixture.get("scheduled_at")
                        or fixture.get("scheduled_date")
                        or ""
                    )

                    display_text = f"{home_name} vs {away_name}"
                    if tournament.get("name"):
                        display_text += f" · {tournament['name']}"
                    if scheduled:
                        display_text += f" · {str(scheduled).replace('T', ' ')}"
                    if venue:
                        display_text += f" · {venue}"

                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, fixture_id)
                    self.fixtures_list.addItem(item)

                self.backend_status_label.setText(
                    f"Found {len(fixtures_to_show)} fixtures"
                )
            else:
                self.backend_status_label.setText("No fixtures found")

            # Reset selection info when list refreshes
            self.selected_fixture_info.setText("Select a fixture to load")
        except Exception as e:
            self.backend_status_label.setText(f"Error: {str(e)}")
    
    def on_tournament_filter_changed(self, index):
        """Handle tournament filter change"""
        tournament_id = self.tournament_combo.currentData()
        self.refresh_fixtures_list(tournament_id)
    
    def on_fixture_double_clicked(self, item):
        """Handle double-click on fixture to load it"""
        self.fixtures_list.setCurrentItem(item)
        self.load_fixture()
    
    def _transform_backend_fixture(self, backend_fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a backend fixture into the format expected by MatchSetupTab."""
        if not backend_fixture:
            return backend_fixture

        def normalize_team(team: Dict[str, Any]) -> Dict[str, Any]:
            team = (team or {}).copy()

            normalized_players: List[Dict[str, Any]] = []
            for player in team.get("players", []):
                full_name = player.get("full_name") or player.get("name") or ""
                normalized_players.append(
                    {
                        "id": player.get("id", ""),
                        "jersey_number": player.get("jersey_number")
                        if player.get("jersey_number") is not None
                        else player.get("number", 0),
                        "full_name": full_name,
                        "name": full_name,
                        "position": player.get("position"),
                        "is_captain": player.get("is_captain", False),
                        "is_starting": player.get("is_starting", False),
                    }
                )

            normalized_kits: List[Dict[str, Any]] = []
            for kit in team.get("kits", []):
                image_url = kit.get("image_url") or kit.get("image_path") or ""
                if image_url and image_url.startswith("/"):
                    image_url = f"http://localhost:8000{image_url}"
                normalized_kits.append(
                    {
                        "type": kit.get("kit_type") or kit.get("type", "home"),
                        "image_url": image_url,
                        "primary_color": kit.get("primary_color"),
                        "secondary_color": kit.get("secondary_color"),
                        "brand_color": kit.get("brand_color"),
                    }
                )

            logo_url = team.get("logo_url") or team.get("logo_path") or ""
            if logo_url and logo_url.startswith("/"):
                logo_url = f"http://localhost:8000{logo_url}"

            return {
                "id": team.get("id"),
                "name": team.get("name"),
                "full_name": team.get("name"),
                "short_name": team.get("short_name"),
                "logo_url": logo_url,
                "primary_color": team.get("primary_color"),
                "secondary_color": team.get("secondary_color"),
                "kits": normalized_kits,
                "players": normalized_players,
            }

        tournament = (backend_fixture.get("tournament") or {}).copy()
        if tournament.get("logo_url", "").startswith("/"):
            tournament["logo_url"] = f"http://localhost:8000{tournament['logo_url']}"

        transformed = {
            "id": backend_fixture.get("id"),
            "home_team": normalize_team(backend_fixture.get("home_team", {})),
            "away_team": normalize_team(backend_fixture.get("away_team", {})),
            "venue": backend_fixture.get("venue"),
            "scheduled_date": backend_fixture.get("scheduled_at")
            or backend_fixture.get("scheduled_date"),
            "matchday": backend_fixture.get("match_day")
            or backend_fixture.get("matchday"),
            "round": backend_fixture.get("round"),
            "status": backend_fixture.get("status"),
            "tournament": tournament,
            "officials": backend_fixture.get("officials", {}),
            "commentators": backend_fixture.get("commentators", {}),
            "hosts": backend_fixture.get("hosts", []),
            "guests": backend_fixture.get("guests", []),
            "organizers": backend_fixture.get("organizers", []),
            "available_officials": backend_fixture.get("available_officials", []),
            "available_commentators": backend_fixture.get("available_commentators", []),
            "available_hosts": backend_fixture.get("available_hosts", []),
        }

        return transformed

    def _transform_cloud_fixture(self, cloud_fixture):
        """Transform cloud fixture format to match expected format for load_fixture_data"""
        if not cloud_fixture:
            return cloud_fixture

        # Transform home_team - merge lineup into players
        home_team = cloud_fixture.get("home_team", {}).copy()
        home_lineup = cloud_fixture.get("home_lineup", [])
        home_subs = cloud_fixture.get("home_substitutes", [])
        
        # Convert players to expected format
        home_players = []
        for p in home_lineup + home_subs:
            home_players.append({
                "id": p.get("id", ""),
                "jersey_number": p.get("number", 0),
                "full_name": p.get("name", ""),
                "name": p.get("name", ""),
                "position": p.get("position", ""),
                "is_captain": p.get("is_captain", False),
                "is_starting": p.get("is_starting", False),
            })
        home_team["players"] = home_players
        home_team["primary_color"] = home_team.get("primary_color", "#2563eb")
        home_team["secondary_color"] = home_team.get("secondary_color", "#000000")
        
        # Transform home kits with image URLs (use local backend proxy)
        home_kits = []
        for kit in home_team.get("kits", []):
            # Convert cloud URL to local backend URL
            image_url = kit.get("image_url", "")
            if image_url.startswith("/assets/"):
                # Proxy through local backend
                image_url = f"http://localhost:8000{image_url}"
            home_kits.append({
                "type": kit.get("type", "home"),
                "image_url": image_url,
                "primary_color": kit.get("primary_color"),
                "secondary_color": kit.get("secondary_color"),
                "brand_color": kit.get("brand_color"),
            })
        home_team["kits"] = home_kits
        
        # Transform logo URL
        if home_team.get("logo_url", "").startswith("/assets/"):
            home_team["logo_url"] = f"http://localhost:8000{home_team['logo_url']}"
        
        # Transform away_team
        away_team = cloud_fixture.get("away_team", {}).copy()
        away_lineup = cloud_fixture.get("away_lineup", [])
        away_subs = cloud_fixture.get("away_substitutes", [])
        
        away_players = []
        for p in away_lineup + away_subs:
            away_players.append({
                "id": p.get("id", ""),
                "jersey_number": p.get("number", 0),
                "full_name": p.get("name", ""),
                "name": p.get("name", ""),
                "position": p.get("position", ""),
                "is_captain": p.get("is_captain", False),
                "is_starting": p.get("is_starting", False),
            })
        away_team["players"] = away_players
        away_team["primary_color"] = away_team.get("primary_color", "#dc2626")
        away_team["secondary_color"] = away_team.get("secondary_color", "#000000")
        
        # Transform away kits with image URLs
        away_kits = []
        for kit in away_team.get("kits", []):
            image_url = kit.get("image_url", "")
            if image_url.startswith("/assets/"):
                image_url = f"http://localhost:8000{image_url}"
            away_kits.append({
                "type": kit.get("type", "home"),
                "image_url": image_url,
                "primary_color": kit.get("primary_color"),
                "secondary_color": kit.get("secondary_color"),
                "brand_color": kit.get("brand_color"),
            })
        away_team["kits"] = away_kits
        
        # Transform logo URL
        if away_team.get("logo_url", "").startswith("/assets/"):
            away_team["logo_url"] = f"http://localhost:8000{away_team['logo_url']}"
        
        # Build transformed fixture
        transformed = {
            "id": cloud_fixture.get("id"),
            "home_team": home_team,
            "away_team": away_team,
            "venue": cloud_fixture.get("venue"),
            "scheduled_date": cloud_fixture.get("scheduled_date"),
            "matchday": cloud_fixture.get("matchday"),
            "round": cloud_fixture.get("round"),
            # Tournament data
            "tournament": cloud_fixture.get("tournament", {}),
            # Officials
            "officials": cloud_fixture.get("officials", {}),
            # Commentators
            "commentators": cloud_fixture.get("commentators", {}),
            # Hosts
            "hosts": cloud_fixture.get("hosts", []),
            # Guests
            "guests": cloud_fixture.get("guests", []),
            # Organizers
            "organizers": cloud_fixture.get("organizers", []),
            # Available pools from tournament
            "available_officials": cloud_fixture.get("available_officials", []),
            "available_commentators": cloud_fixture.get("available_commentators", []),
            "available_hosts": cloud_fixture.get("available_hosts", []),
        }
        
        return transformed
        
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
            if self.backend_radio.isChecked():
                # Load from backend
                selected_item = self.fixtures_list.currentItem()
                if not selected_item:
                    QMessageBox.warning(self, "Warning", "Please select a fixture from the list.")
                    return
                
                fixture_id = selected_item.data(Qt.UserRole)
                if get_api is None:
                    QMessageBox.warning(self, "Error", "Backend API not available")
                    return
                
                api = get_api()
                
                progress = QProgressDialog(
                    "Loading fixture from backend...", None, 0, 0, self
                )
                progress.setWindowTitle("Loading")
                progress.setModal(True)
                progress.show()

                try:
                    backend_fixture = api.get_fixture(fixture_id)
                    if backend_fixture:
                        data = self._transform_backend_fixture(backend_fixture)
                    else:
                        QMessageBox.warning(
                            self, "Error", "Failed to load fixture from backend"
                        )
                        return
                finally:
                    progress.close()
                
            elif self.file_radio.isChecked():
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
