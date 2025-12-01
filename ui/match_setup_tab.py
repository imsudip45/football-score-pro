"""
Match Setup Tab for Football Score Pro 2.0
Main container for the modular Match Setup interface
Based on the old Game Settings UI but integrated with new backend architecture
"""

import re

# Import Team model for backend compatibility
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .backend_service import BackendService
from .backend_sync import sync_match_snapshot
from .widgets.officials_tab import OfficialsTab
from .widgets.team_panel import TeamPanel

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.constants import TeamConstants


class MatchSetupTab(QWidget):
    """Main Match Setup Tab that orchestrates all components"""

    # Signal for match data changes
    match_data_changed = Signal(dict)
    match_created = Signal(str)  # match_id
    match_saved = Signal(str)  # file_path

    def __init__(self, backend_service: BackendService, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service
        # Track whether we are performing the initial fixture load
        self._is_initial_fixture_load = False
        # Global per-team colors (shared across panels)
        self.pool_a_color_1 = "#000000"
        self.pool_b_color_1 = "#000000"

        # Global state management (like old Game_Setting.py)
        self.a_selected_rows = set()  # Global selected rows for Team A
        self.b_selected_rows = set()  # Global selected rows for Team B
        self.pool_a_formation = "Select Formation"  # Global formation for Team A
        self.pool_b_formation = "Select Formation"  # Global formation for Team B
        # Kit selection pools (0 = Home Kit, 1 = Away Kit, 2 = Third Kit)
        self.pool_a_kit_index = 0  # Global kit index for Team A
        self.pool_b_kit_index = 0  # Global kit index for Team B
        self.pool_a_allow_fixture_defaults = True
        self.pool_b_allow_fixture_defaults = True
        # Global player position pools (shared across Home/Away panels)
        self.pool_a_positions = {}  # Global saved positions for Team A players
        self.pool_b_positions = {}  # Global saved positions for Team B players
        self.current_match_id = None

        # Initialize components
        self.home_team_panel = TeamPanel("Home Team", self.backend_service, self)
        self.away_team_panel = TeamPanel("Away Team", self.backend_service, self)
        self.officials_tab = OfficialsTab(self.backend_service, self)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create tabs widget first
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self.get_tab_style())

        # Hide the default tab bar since we're using custom buttons
        self.tabs.tabBar().setVisible(False)

        # Add team tabs
        self.tabs.addTab(self.home_team_panel, "Home Team")
        self.tabs.addTab(self.away_team_panel, "Away Team")
        self.tabs.addTab(self.officials_tab, "Officials")

        # Create custom header with tab buttons, match number, and create match button
        header_layout = self.create_header_layout()
        layout.addLayout(header_layout)

        # Add the tabs content area (without the tab buttons)
        layout.addWidget(self.tabs)

    def create_header_layout(self):
        """Create header layout with custom tab buttons, match number, and create match button"""
        header_layout = QHBoxLayout()

        # Create custom tab buttons
        self.home_tab_button = QPushButton("Home Team")
        self.away_tab_button = QPushButton("Away Team")
        self.officials_tab_button = QPushButton("Officials")

        # Style the tab buttons
        self.home_tab_button.setStyleSheet(self.get_tab_button_style(True))  # Active
        self.away_tab_button.setStyleSheet(self.get_tab_button_style(False))  # Inactive
        self.officials_tab_button.setStyleSheet(
            self.get_tab_button_style(False)
        )  # Inactive

        # Connect tab button signals
        self.home_tab_button.clicked.connect(lambda: self.switch_tab(0))
        self.away_tab_button.clicked.connect(lambda: self.switch_tab(1))
        self.officials_tab_button.clicked.connect(lambda: self.switch_tab(2))

        # Add tab buttons to layout
        header_layout.addWidget(self.home_tab_button)
        header_layout.addWidget(self.away_tab_button)
        header_layout.addWidget(self.officials_tab_button)

        # Add spacer
        header_layout.addStretch()

        # Match number controls with separate arrows
        match_label = QLabel("MATCH NO:")
        match_label.setStyleSheet("""
            QLabel {
                color: #e5e7eb;
                font-size: 20px;
                font-weight: 600;
                padding: 5px;
            }
        """)

        # Match number input field
        self.match_input = QLineEdit("1")
        self.match_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.match_input.setFixedSize(80, 40)
        self.match_input.setFont(QFont("Verdana", 20, QFont.Weight.Bold))
        self.match_input.setStyleSheet("""
            QLineEdit {
                background-color: #00AA00;
                    color: white;
                font-weight: bold;
                    border-radius: 8px;
                border: 2px solid gray;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
            }
        """)

        # Up arrow button
        self.match_up_button = QPushButton("\u25b2")
        self.match_up_button.setFixedSize(32, 24)
        self.match_up_button.setFont(QFont("Verdana", 16, QFont.Weight.Bold))
        self.match_up_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                    font-weight: bold;
                border-radius: 3px;
                border: 1px solid #4b5563;
                margin: 0px;
                padding: 4px;
                }
                QPushButton:hover {
                background-color: #374151;
                border: 1px solid #6b7280;
                }
        """)

        # Down arrow button
        self.match_down_button = QPushButton("\u25bc")
        self.match_down_button.setFixedSize(32, 24)
        self.match_down_button.setFont(QFont("Verdana", 16, QFont.Weight.Bold))
        self.match_down_button.setStyleSheet("""
                QPushButton {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                    font-weight: bold;
                border-radius: 3px;
                border: 1px solid #4b5563;
                margin: 0px;
                padding: 4px;
                }
                QPushButton:hover {
                background-color: #374151;
                border: 1px solid #6b7280;
                }
        """)

        # Connect button signals
        self.match_up_button.clicked.connect(self.increment_match_number)
        self.match_down_button.clicked.connect(self.decrement_match_number)
        self.match_input.editingFinished.connect(self.on_match_number_changed)

        # Create vertical layout for arrow buttons
        arrow_layout = QVBoxLayout()
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.setSpacing(0)
        arrow_layout.addWidget(self.match_up_button)
        arrow_layout.addWidget(self.match_down_button)

        # Create container widget for arrow buttons
        arrow_container = QWidget()
        arrow_container.setLayout(arrow_layout)
        arrow_container.setFixedSize(
            32, 48
        )  # Width matches button width, height for both buttons

        # Add widgets to layout with minimal spacing
        header_layout.addWidget(match_label)
        header_layout.addWidget(self.match_input)

        # Add arrow container with minimal gap
        header_layout.addSpacing(2)  # Very small gap
        header_layout.addWidget(arrow_container)

        # Create Match button
        self.create_match_button = QPushButton("CREATE MATCH")
        self.create_match_button.setStyleSheet(self.get_create_button_style())
        self.create_match_button.clicked.connect(self.create_match)

        header_layout.addWidget(self.create_match_button)

        return header_layout

    def switch_tab(self, index: int):
        """Switch to the specified tab"""
        self.tabs.setCurrentIndex(index)

        # Update button styles
        self.home_tab_button.setStyleSheet(self.get_tab_button_style(index == 0))
        self.away_tab_button.setStyleSheet(self.get_tab_button_style(index == 1))
        self.officials_tab_button.setStyleSheet(self.get_tab_button_style(index == 2))

    def connect_signals(self):
        """Connect all signals"""
        # Connect team panel signals
        self.home_team_panel.data_changed.connect(self.on_data_changed)
        self.away_team_panel.data_changed.connect(self.on_data_changed)

        # Connect formation panel data source changes (like old Game_Setting.py)
        self.home_team_panel.formation_panel.data_changed.connect(
            self.on_home_team_data_source_changed
        )
        self.away_team_panel.formation_panel.data_changed.connect(
            self.on_away_team_data_source_changed
        )

        # Connect officials tab signals
        self.officials_tab.data_changed.connect(self.on_data_changed)

        # Match number input already calls on_data_changed via helper methods

    def on_data_changed(self):
        """Handle data changes from any component"""
        self.match_data_changed.emit(self.get_match_data())

    def get_match_data(self) -> dict:
        """Get complete match data from all components"""
        try:
            # Get team data
            home_team_data = self.home_team_panel.get_team_data()
            away_team_data = self.away_team_panel.get_team_data()

            # Get officials data
            officials_data = self.officials_tab.get_officials_data()

            # Combine all data
            match_data = {
                "match_id": self.current_match_id,
                "match_number": self.get_match_number(),
                "home_team": home_team_data,
                "away_team": away_team_data,
                "officials": officials_data,
                "created_at": None,  # Will be set when match is created
                "status": "setup",  # Match is in setup phase
            }

            return match_data

        except Exception:
            return {}

    def export_state(self) -> dict:
        """Return a serializable snapshot of the current match setup state."""
        try:
            state = {"match_data": self.get_match_data()}
            if hasattr(self, "home_team_panel"):
                state["home_panel_state"] = self.home_team_panel.export_state()
            if hasattr(self, "away_team_panel"):
                state["away_panel_state"] = self.away_team_panel.export_state()
            state["pool_state"] = {
                "pool_a_color_1": getattr(self, "pool_a_color_1", "#000000"),
                "pool_b_color_1": getattr(self, "pool_b_color_1", "#000000"),
                "pool_a_kit_index": getattr(self, "pool_a_kit_index", 0),
                "pool_b_kit_index": getattr(self, "pool_b_kit_index", 0),
                "pool_a_formation": getattr(
                    self, "pool_a_formation", "Select Formation"
                ),
                "pool_b_formation": getattr(
                    self, "pool_b_formation", "Select Formation"
                ),
            }
            return state
        except Exception as exc:
            print(f"Error exporting match setup state: {exc}")
            return {"match_data": self.get_match_data()}

    def load_match_state(self, state: dict):
        """Load match setup UI from a saved state dictionary."""
        try:
            if not state:
                return
            match_data = state.get("match_data") if isinstance(state, dict) else state
            if isinstance(match_data, dict):
                self.current_match_id = match_data.get(
                    "match_id", self.current_match_id
                )
                self.load_match_data(match_data)
            pool_state = state.get("pool_state", {})
            self.pool_a_color_1 = pool_state.get("pool_a_color_1", self.pool_a_color_1)
            self.pool_b_color_1 = pool_state.get("pool_b_color_1", self.pool_b_color_1)
            self.pool_a_kit_index = pool_state.get(
                "pool_a_kit_index", self.pool_a_kit_index
            )
            self.pool_b_kit_index = pool_state.get(
                "pool_b_kit_index", self.pool_b_kit_index
            )
            self.pool_a_formation = pool_state.get(
                "pool_a_formation", self.pool_a_formation
            )
            self.pool_b_formation = pool_state.get(
                "pool_b_formation", self.pool_b_formation
            )
            if "home_panel_state" in state and hasattr(self, "home_team_panel"):
                self.home_team_panel.load_state(state["home_panel_state"])
            if "away_panel_state" in state and hasattr(self, "away_team_panel"):
                self.away_team_panel.load_state(state["away_panel_state"])
            if isinstance(match_data, dict):
                self.match_data_changed.emit(match_data)
        except Exception as exc:
            print(f"Error loading match state: {exc}")

    def load_fixture_data(self, fixture_data: dict):
        """Load fixture data and update both team panels"""
        try:
            # Mark that we are in initial fixture load so colors can be initialized from fixture
            self._is_initial_fixture_load = True

            # Extract team data from fixture - handle different formats
            home_team_data = None
            away_team_data = None

            # Check if it's the new format with teams array
            if "teams" in fixture_data and isinstance(fixture_data["teams"], list):
                teams = fixture_data["teams"]
                for team in teams:
                    if team.get("id") == "A":
                        home_team_data = team
                    elif team.get("id") == "B":
                        away_team_data = team
            # Check if it's the old format with home_team/away_team keys
            elif "home_team" in fixture_data and "away_team" in fixture_data:
                home_team_data = fixture_data.get("home_team", {})
                away_team_data = fixture_data.get("away_team", {})

            # Store team data for global access
            if home_team_data:
                self.home_team_data = self._format_team_data(home_team_data)
                self.pool_a_allow_fixture_defaults = True
                # Initialize global pool color for Team A from fixture
                self.pool_a_color_1 = self.home_team_data.get(
                    "color_1", self.pool_a_color_1
                )

            if away_team_data:
                self.away_team_data = self._format_team_data(away_team_data)
                self.pool_b_allow_fixture_defaults = True
                # Initialize global pool color for Team B from fixture
                self.pool_b_color_1 = self.away_team_data.get(
                    "color_1", self.pool_b_color_1
                )

            # Preload panels with both teams so radio labels/formation reflect immediately

            if hasattr(self, "home_team_panel"):
                if hasattr(self, "home_team_data"):
                    self.home_team_panel.team_a_data = self.home_team_data.copy()
                    self.home_team_panel.team_a_formation = "Select Formation"
                if hasattr(self, "away_team_data"):
                    self.home_team_panel.team_b_data = self.away_team_data.copy()
                    self.home_team_panel.team_b_formation = "Select Formation"

            if hasattr(self, "away_team_panel"):
                if hasattr(self, "home_team_data"):
                    self.away_team_panel.team_a_data = self.home_team_data.copy()
                    self.away_team_panel.team_a_formation = "Select Formation"
                if hasattr(self, "away_team_data"):
                    self.away_team_panel.team_b_data = self.away_team_data.copy()
                    self.away_team_panel.team_b_formation = "Select Formation"

            # Update radio button labels with team names for both panels (if both teams available)
            if hasattr(self, "home_team_data") and hasattr(self, "away_team_data"):
                self.home_team_panel.update_radio_short_names(
                    self.home_team_data, self.away_team_data
                )
                self.away_team_panel.update_radio_short_names(
                    self.home_team_data, self.away_team_data
                )
                self.home_team_panel.refresh_formation_labels()
                self.away_team_panel.refresh_formation_labels()

            # Load initial team data (Home shows Team A, Away shows Team B)
            if hasattr(self, "home_team_data"):
                self.update_player_table(
                    self.home_team_panel, self.home_team_data, "home", "a"
                )
            if hasattr(self, "away_team_data"):
                self.update_player_table(
                    self.away_team_panel, self.away_team_data, "away", "b"
                )

            # Load tournament data if available
            tournament_data = fixture_data.get("tournament", {})
            if tournament_data:
                self.officials_tab.load_tournament_data(tournament_data)

            # Load officials pool from fixture if available (for selector dialog)
            # Check for _parent_data first (from multi-fixture tournament files)
            parent_data = fixture_data.get("_parent_data", {})
            if parent_data:
                # Extract from parent_data (root level of multi-fixture JSON)
                officials_pool_data = {
                    "available_officials": parent_data.get("available_officials"),
                    "available_commentators": parent_data.get("available_commentators"),
                    "available_hosts": parent_data.get("available_hosts"),
                }
            else:
                # Try extracting from fixture_data directly (single fixture or legacy format)
                officials_pool_data = (
                    self.backend_service.extract_officials_pool_from_fixture(
                        fixture_data
                    )
                )

            if officials_pool_data:
                # Build pool data structure for load_officials_pool
                pool_to_load = {}

                # Extract available_officials (contains referees, assistant_referees, etc.)
                if (
                    "available_officials" in officials_pool_data
                    and officials_pool_data["available_officials"]
                ):
                    available_officials = officials_pool_data["available_officials"]
                    if isinstance(available_officials, dict):
                        normalized_pool = self._normalize_available_officials_pool(
                            available_officials
                        )
                        pool_to_load.update(normalized_pool)
                        self.officials_tab.load_officials_data(available_officials)

                # Add commentators if available
                if (
                    "available_commentators" in officials_pool_data
                    and officials_pool_data["available_commentators"]
                ):
                    pool_to_load["commentators"] = officials_pool_data[
                        "available_commentators"
                    ]

                # Add hosts if available
                if (
                    "available_hosts" in officials_pool_data
                    and officials_pool_data["available_hosts"]
                ):
                    pool_to_load["hosts"] = officials_pool_data["available_hosts"]

                if pool_to_load:
                    # Load the officials pool into the backend service
                    tournament_id = (
                        tournament_data.get("id") if tournament_data else None
                    )
                    print(
                        "MatchSetupTab: Loading officials pool with",
                        len(pool_to_load),
                        "categories",
                    )
                    result = self.backend_service.load_officials_pool(
                        pool_to_load, tournament_id
                    )
                    if result.success:
                        print("MatchSetupTab: Officials pool loaded successfully")
                    else:
                        print(
                            f"MatchSetupTab: Failed to load officials pool: {result.errors}"
                        )
                else:
                    print("MatchSetupTab: No officials pool data to load")
            else:
                print("MatchSetupTab: No officials pool data found in fixture")

            # DON'T automatically load officials data into the UI - let user manually select
            # The officials pool is still loaded above for the selector dialog to work
            # officials_data = fixture_data.get("officials", {})
            # if officials_data:
            #     normalized_officials = self._normalize_officials_data(
            #         officials_data,
            #         tournament_data if tournament_data else None,
            #     )
            #     if normalized_officials:
            #         self.officials_tab.set_officials(normalized_officials)
            # Initial fixture load complete
            self._is_initial_fixture_load = False

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load fixture: {str(e)}")

    def _normalize_available_officials_pool(
        self, available_officials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert panel-based officials arrays into backend pool categories."""
        normalized: Dict[str, Any] = {}
        if not isinstance(available_officials, dict):
            return normalized

        officials_panel = available_officials.get("officials_panel")
        if officials_panel:
            normalized["referees"] = officials_panel
            normalized.setdefault("linesmen", officials_panel)
            normalized.setdefault("fourth_officials", officials_panel)
            normalized.setdefault("var_referees", officials_panel)
        else:
            for legacy_key in (
                "referees",
                "linesmen",
                "fourth_officials",
                "var_referees",
            ):
                if legacy_key in available_officials:
                    normalized[legacy_key] = available_officials[legacy_key]

        if "commentators_panel" in available_officials:
            normalized["commentators"] = available_officials["commentators_panel"]
        elif "commentators" in available_officials:
            normalized["commentators"] = available_officials["commentators"]

        if "hosts_panel" in available_officials:
            normalized["hosts"] = available_officials["hosts_panel"]
        elif "hosts" in available_officials:
            normalized["hosts"] = available_officials["hosts"]

        if (
            "available_commentators" in available_officials
            and "commentators" not in normalized
        ):
            normalized["commentators"] = available_officials["available_commentators"]
        if "available_hosts" in available_officials and "hosts" not in normalized:
            normalized["hosts"] = available_officials["available_hosts"]

        return normalized

    def _format_team_data(self, team_data: dict) -> dict:
        """Convert team data from fixture format to TeamPanel format"""
        try:
            # Convert players to the format expected by TeamPanel
            players = []
            for player in team_data.get("players", []):
                player_dict = {
                    "jersey_number": player.get("jersey_number", 0),
                    "name": player.get("full_name", ""),
                    "id": player.get("id", ""),
                    "position": player.get("position", ""),
                    "selected": False,  # Default to not selected
                }
                players.append(player_dict)

            # Format team data
            kits = team_data.get("kits", [])

            formatted_team = {
                "id": team_data.get("id", ""),
                "name": team_data.get("name", ""),
                "full_name": team_data.get("full_name", ""),
                "short_name": team_data.get("short_name", ""),
                "manager": team_data.get("head_coach", ""),
                "head_coach": team_data.get("head_coach", ""),
                "formation": team_data.get("formation", "Select Formation"),
                "color_1": team_data.get("primary_color", "#2563eb"),
                "color_2": team_data.get("secondary_color", "#000000"),
                "color_mode": "gradient"
                if team_data.get("secondary_color")
                else "single",
                "logo": team_data.get("logo"),  # Include logo from fixture
                "logo_url": team_data.get("logo_url"),  # Include logo_url as fallback
                "kit_image": team_data.get(
                    "kit_image", None
                ),  # Kit image filename from JSON
                "kits": kits,  # Kits array from JSON (home, away, third)
                "players": players,
            }

            return formatted_team

        except Exception:
            return team_data  # Return original data if formatting fails

    def _normalize_officials_data(
        self, officials_raw: Any, tournament_fallback: Optional[dict] = None
    ) -> Dict[str, Any]:
        """Normalize officials payload from fixture JSON for OfficialsTab."""
        if not officials_raw:
            return {}

        if isinstance(officials_raw, list):
            flattened: Dict[str, Any] = {}
            for entry in officials_raw:
                if not isinstance(entry, dict):
                    continue
                role = entry.get("role") or entry.get("position") or entry.get("title")
                if not role:
                    continue
                flattened[role] = entry
            normalized = self._normalize_officials_from_dict(flattened)
        elif isinstance(officials_raw, dict):
            normalized = self._normalize_officials_from_dict(officials_raw)
        else:
            return {}

        if tournament_fallback and "tournament" not in normalized:
            normalized["tournament"] = tournament_fallback
        return normalized

    def _normalize_officials_from_dict(self, data: Dict[Any, Any]) -> Dict[str, Any]:
        """Normalize dictionary-shaped officials payload."""
        normalized: Dict[str, Any] = {}
        hosts: List[str] = []
        organizers: List[str] = []
        commentators_first: List[str] = []
        commentators_second: List[str] = []
        guests: Dict[str, Dict[str, Any]] = {}

        for key, value in data.items():
            canonical = self._canonicalize_role(key)

            if canonical == "tournament":
                if isinstance(value, dict):
                    normalized["tournament"] = value
                continue

            if canonical in {"hosts", "host_list"}:
                hosts = self._normalize_names_list(value)
                continue

            if canonical in {"organizers", "organiser_list", "organizer_list"}:
                organizers = self._normalize_names_list(value)
                continue

            if canonical in {"commentators_1st", "commentators_first_half"}:
                commentators_first = self._normalize_names_list(value)
                continue

            if canonical in {"commentators_2nd", "commentators_second_half"}:
                commentators_second = self._normalize_names_list(value)
                continue

            if canonical == "guests":
                guests = self._normalize_guests_block(value)
                continue

            base_key, slot = self._split_role_key(canonical)
            name = self._extract_official_name(value)

            if not name and base_key not in {"var_referee", "avar_referee"}:
                continue

            if base_key in {"referee", "main_referee", "center_referee"}:
                normalized["referee"] = name
                continue

            if base_key in {"fourth_official", "fourth_referee"}:
                normalized["fourth_official"] = name
                continue

            if base_key in {"var_referee", "var"}:
                normalized["var_referee"] = name
                continue

            if base_key in {"avar_referee", "avar"}:
                normalized["avar_referee"] = name
                continue

            if base_key in {"assistant_referee", "assistant", "linesman"} and slot:
                idx = 1 if slot <= 1 else 2
                normalized[f"assistant_referee_{idx}"] = name
                continue

            if base_key in {"host", "hosts"} and slot:
                self._assign_indexed_value(hosts, slot - 1, name)
                continue

            if base_key in {"organizer", "organiser"} and slot:
                self._assign_indexed_value(organizers, slot - 1, name)
                continue

            if base_key.startswith("commentator"):
                target = (
                    commentators_second
                    if (
                        "second" in base_key or "2nd" in base_key or (slot and slot > 3)
                    )
                    else commentators_first
                )
                position = (slot - 1) if slot else len(target)
                if target is commentators_second and slot and slot > 3:
                    position = slot - 4
                self._assign_indexed_value(target, max(position, 0), name)
                continue

            if base_key.startswith("guest"):
                guest_id = (
                    f"guest{slot}" if slot else base_key.replace("guest_", "guest")
                )
                entry = self._normalize_guest_entry(value)
                if entry:
                    guests[guest_id] = entry
                continue

        if hosts:
            normalized["hosts"] = hosts
        if organizers:
            normalized["organizers"] = organizers
        if commentators_first:
            normalized["commentators_1st"] = commentators_first
        if commentators_second:
            normalized["commentators_2nd"] = commentators_second
        if guests:
            normalized["guests"] = guests

        return normalized

    @staticmethod
    def _normalize_names_list(source: Any) -> List[str]:
        """Normalize a list-like payload into a list of names."""
        names: List[str] = []
        if isinstance(source, (list, tuple)):
            for idx, entry in enumerate(source):
                name = MatchSetupTab._extract_official_name(entry)
                if name:
                    MatchSetupTab._assign_indexed_value(names, idx, name)
        elif isinstance(source, dict):
            for key, entry in source.items():
                base, slot = MatchSetupTab._split_role_key(
                    MatchSetupTab._canonicalize_role(key)
                )
                name = MatchSetupTab._extract_official_name(entry)
                if name:
                    target_index = slot - 1 if slot else len(names)
                    MatchSetupTab._assign_indexed_value(names, target_index, name)
        else:
            name = MatchSetupTab._extract_official_name(source)
            if name:
                names.append(name)
        return names

    @staticmethod
    def _normalize_guests_block(source: Any) -> Dict[str, Dict[str, Any]]:
        """Normalize guests payload to guestX dictionary."""
        guests: Dict[str, Dict[str, Any]] = {}
        if isinstance(source, dict):
            for guest_key, guest_value in source.items():
                canonical = MatchSetupTab._canonicalize_role(guest_key)
                base, slot = MatchSetupTab._split_role_key(canonical)
                if base != "guest":
                    continue
                guest_id = f"guest{slot}" if slot else guest_key
                entry = MatchSetupTab._normalize_guest_entry(guest_value)
                if entry:
                    guests[guest_id] = entry
        elif isinstance(source, (list, tuple)):
            for idx, entry in enumerate(source, 1):
                normalized_entry = MatchSetupTab._normalize_guest_entry(entry)
                if normalized_entry:
                    guests[f"guest{idx}"] = normalized_entry
        else:
            entry = MatchSetupTab._normalize_guest_entry(source)
            if entry:
                guests["guest1"] = entry
        return guests

    @staticmethod
    def _normalize_guest_entry(value: Any) -> Dict[str, Any]:
        """Convert guest entry to a dictionary with at least full_name."""
        if isinstance(value, dict):
            result = dict(value)
            if not result.get("full_name"):
                name = MatchSetupTab._extract_official_name(value)
                if name:
                    result["full_name"] = name
            return result
        name = MatchSetupTab._extract_official_name(value)
        return {"full_name": name} if name else {}

    @staticmethod
    def _assign_indexed_value(target_list: List[str], index: int, value: str):
        """Set value in list ensuring size."""
        if index < 0 or not value:
            return
        while len(target_list) <= index:
            target_list.append("")
        target_list[index] = value

    @staticmethod
    def _canonicalize_role(role: Any) -> str:
        """Convert arbitrary role text to a normalized snake_case key."""
        return re.sub(r"[^a-z0-9]+", "_", str(role).strip().lower()).strip("_")

    @staticmethod
    def _split_role_key(key: str) -> Tuple[str, Optional[int]]:
        """Split a normalized key into base and trailing integer slot."""
        match = re.search(r"(\d+)$", key)
        if not match:
            return key, None
        slot = int(match.group(1))
        base = key[: match.start()].rstrip("_")
        return base, slot

    @staticmethod
    def _extract_official_name(value: Any) -> str:
        """Extract a displayable name from different value shapes."""
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in (
                "full_name",
                "name",
                "short_name",
                "display_name",
                "title",
                "label",
                "value",
                "text",
            ):
                if value.get(key):
                    return str(value[key])
            return ""
        if isinstance(value, (list, tuple)) and value:
            return MatchSetupTab._extract_official_name(value[0])
        return str(value) if value not in ("", None) else ""

    def update_player_table(self, team_panel, team_data, team_type, radio_state):
        """Update player table with team data and apply saved selections (like old Game_Setting.py)
        Colors: during the initial fixture load, allow incoming fixture colors to initialize the panel.
        Outside of initial load, avoid overwriting user-chosen colors by not persisting fixture colors.
        """
        try:
            # Get the appropriate selected rows and formation from global state
            selected_rows = (
                self.a_selected_rows if radio_state == "a" else self.b_selected_rows
            )
            formation = (
                self.pool_a_formation if radio_state == "a" else self.pool_b_formation
            )
            allow_fixture_default = (
                self.pool_a_allow_fixture_defaults
                if radio_state == "a"
                else self.pool_b_allow_fixture_defaults
            )

            # Update the team panel with the data
            # Persist colors only during the initial fixture load
            persist_color = bool(getattr(self, "_is_initial_fixture_load", False))

            # Set restoring flag to prevent save during restoration
            team_panel.restoring_selections = True

            try:
                # IMPORTANT: Apply saved selections AFTER set_team_data populates the table
                # Use QTimer to ensure populate_players completes first
                def apply_selections_after_populate():
                    # Apply the saved selections to the player table (both panels should sync for same team)
                    # ALWAYS apply (even if empty) to restore cleared selections
                    if hasattr(team_panel, "player_table"):
                        # Block signals to prevent premature triggering
                        team_panel.player_table.blockSignals(True)

                        # Apply selected rows (even if empty list)
                        team_panel.player_table.apply_selected_rows(list(selected_rows))

                        # Unblock signals
                        team_panel.player_table.blockSignals(False)
                        if selected_rows:
                            print(
                                f"Applied {len(selected_rows)} saved selections to {team_type} table"
                            )
                    else:
                        print(
                            f"Applied empty selections (cleared) to {team_type} table"
                        )

                # Set team data first (this will populate the table)
                preserve_formation = not allow_fixture_default
                team_panel.set_team_data(
                    team_data,
                    f"Team {'A' if radio_state == 'a' else 'B'}",
                    persist_color=persist_color,
                    preserve_formation=preserve_formation,
                )

                # Apply selections after table is populated (with a small delay to ensure populate_players completes)
                QTimer.singleShot(50, apply_selections_after_populate)
            finally:
                # Always reset restoring flag after a short delay to allow selection application
                QTimer.singleShot(
                    100, lambda: setattr(team_panel, "restoring_selections", False)
                )

            # Decide which formation to apply:
            formation_to_apply = formation
            incoming_formation = team_data.get("formation")
            if (
                allow_fixture_default
                and (not formation or formation == "Select Formation")
                and incoming_formation
            ):
                formation_to_apply = incoming_formation
                # Update global pools with fixture formation so future loads use it
                if radio_state == "a":
                    self.pool_a_formation = incoming_formation
                    self.pool_a_allow_fixture_defaults = False  # pool defaults to false
                else:
                    self.pool_b_formation = incoming_formation
                    self.pool_b_allow_fixture_defaults = False

            # Apply the resolved formation
            formation_widget = getattr(
                getattr(team_panel, "control_panel", None), "formation_input", None
            )
            if formation_widget and formation_to_apply is not None:
                formation_widget.blockSignals(True)
                if formation_to_apply == "Select Formation":
                    formation_widget.clear()
                else:
                    formation_widget.setText(formation_to_apply)
                formation_widget.blockSignals(False)
                # Also update the panel's internal formation state since we blocked signals
                if hasattr(team_panel, "current_data_source"):
                    if team_panel.current_data_source == "Team A" and hasattr(
                        team_panel, "team_a_formation"
                    ):
                        team_panel.team_a_formation = formation_to_apply
                    elif team_panel.current_data_source == "Team B" and hasattr(
                        team_panel, "team_b_formation"
                    ):
                        team_panel.team_b_formation = formation_to_apply

            # Update formation labels in FormationPanel
            if hasattr(team_panel, "formation_panel"):
                if radio_state == "a":
                    team_panel.formation_panel.update_team_a_formation(
                        formation_to_apply or "Select Formation"
                    )
                else:
                    team_panel.formation_panel.update_team_b_formation(
                        formation_to_apply or "Select Formation"
                    )

            # Re-apply formation after the UI settles to ensure markers render immediately
            # Delay slightly so table checkboxes and combo changes are fully processed
            if hasattr(team_panel, "apply_current_formation"):

                def apply_and_persist():
                    team_panel.apply_current_formation()
                    current_form = formation_to_apply or "Select Formation"
                    if radio_state == "a":
                        self.pool_a_formation = current_form
                    else:
                        self.pool_b_formation = current_form

                QTimer.singleShot(0, apply_and_persist)
                # No need to force scaling since we now use consistent scene rectangles

            if hasattr(team_panel, "refresh_formation_labels"):
                team_panel.refresh_formation_labels()

        except Exception:
            pass

    def on_home_team_data_source_changed(self):
        """Handle home team data source change (like old Game_Setting.py)"""
        try:
            # Get current data source from home team panel
            data_source = self.home_team_panel.formation_panel.get_current_data_source()
            radio_state = "a" if data_source == "Team A" else "b"

            # Save current home team state to global pools BEFORE switching
            self.save_home_team_state_to_pools()

            # Update away team panel to show opposite selection
            if radio_state == "a":
                self.away_team_panel.formation_panel.set_data_source_without_emit(
                    "Team B"
                )
            else:
                self.away_team_panel.formation_panel.set_data_source_without_emit(
                    "Team A"
                )

            # Load appropriate team data and apply saved state
            if radio_state == "a":
                # Home team shows Team A data, Away team shows Team B data
                if hasattr(self, "home_team_data") and self.home_team_data:
                    self.update_player_table(
                        self.home_team_panel, self.home_team_data, "home", "a"
                    )
                if hasattr(self, "away_team_data") and self.away_team_data:
                    self.update_player_table(
                        self.away_team_panel, self.away_team_data, "away", "b"
                    )
            else:
                # Home team shows Team B data, Away team shows Team A data
                if hasattr(self, "away_team_data") and self.away_team_data:
                    self.update_player_table(
                        self.home_team_panel, self.away_team_data, "home", "b"
                    )
                if hasattr(self, "home_team_data") and self.home_team_data:
                    self.update_player_table(
                        self.away_team_panel, self.home_team_data, "away", "a"
                    )

        except Exception:
            pass

    def on_away_team_data_source_changed(self):
        """Handle away team data source change (like old Game_Setting.py)"""
        try:
            # Get current data source from away team panel
            data_source = self.away_team_panel.formation_panel.get_current_data_source()
            radio_state = "a" if data_source == "Team A" else "b"

            # Save current away team state to global pools BEFORE switching
            self.save_away_team_state_to_pools()

            # Update home team panel to show opposite selection
            if radio_state == "a":
                self.home_team_panel.formation_panel.set_data_source_without_emit(
                    "Team B"
                )
            else:
                self.home_team_panel.formation_panel.set_data_source_without_emit(
                    "Team A"
                )

            # Load appropriate team data and apply saved state
            if radio_state == "a":
                # Away team shows Team A data, Home team shows Team B data
                if hasattr(self, "home_team_data") and self.home_team_data:
                    self.update_player_table(
                        self.away_team_panel, self.home_team_data, "away", "a"
                    )
                if hasattr(self, "away_team_data") and self.away_team_data:
                    self.update_player_table(
                        self.home_team_panel, self.away_team_data, "home", "b"
                    )
            else:
                # Away team shows Team B data, Home team shows Team A data
                if hasattr(self, "away_team_data") and self.away_team_data:
                    self.update_player_table(
                        self.away_team_panel, self.away_team_data, "away", "b"
                    )
                if hasattr(self, "home_team_data") and self.home_team_data:
                    self.update_player_table(
                        self.home_team_panel, self.home_team_data, "home", "a"
                    )

        except Exception:
            pass

    def save_home_team_state_to_pools(self):
        """Save home team state to global pools"""
        try:
            # Use OLD data source from current_data_source (before it was updated)
            # This is what we're leaving, so we save to this pool
            home_data_source = (
                self.home_team_panel.current_data_source
                if hasattr(self.home_team_panel, "current_data_source")
                else self.home_team_panel.formation_panel.get_current_data_source()
            )

            # Get current selections and formation from home team panel
            # Note: on_formation_data_changed in team_panel.py already saves selections BEFORE clearing the table
            # So if the table is already cleared (empty selections), don't overwrite the saved selections
            if hasattr(self.home_team_panel, "player_table"):
                home_selections = self.home_team_panel.player_table.get_selected_rows()
                if home_data_source == "Team A":
                    home_formation = getattr(
                        self.home_team_panel,
                        "team_a_formation",
                        TeamConstants.SELECT_FORMATION,
                    )
                else:
                    home_formation = getattr(
                        self.home_team_panel,
                        "team_b_formation",
                        TeamConstants.SELECT_FORMATION,
                    )

                # Only save if selections are not empty OR if the pool for this data source is already empty
                # This prevents overwriting saved selections with empty set after table is cleared
                if home_selections:
                    # Selections exist, save them
                    if home_data_source == "Team A":
                        self.a_selected_rows = home_selections.copy()
                        self.pool_a_formation = home_formation
                    else:
                        self.b_selected_rows = home_selections.copy()
                        self.pool_b_formation = home_formation
                elif home_data_source == "Team A" and not self.a_selected_rows:
                    # Selections are empty AND pool is empty - preserve empty state
                    self.a_selected_rows = home_selections.copy()
                    self.pool_a_formation = home_formation
                elif home_data_source == "Team B" and not self.b_selected_rows:
                    # Selections are empty AND pool is empty - preserve empty state
                    self.b_selected_rows = home_selections.copy()
                    self.pool_b_formation = home_formation
                # Otherwise, selections are empty but pool has saved selections - don't overwrite

        except Exception:
            pass

    def save_away_team_state_to_pools(self):
        """Save away team state to global pools"""
        try:
            # Use OLD data source from current_data_source (before it was updated)
            # This is what we're leaving, so we save to this pool
            away_data_source = (
                self.away_team_panel.current_data_source
                if hasattr(self.away_team_panel, "current_data_source")
                else self.away_team_panel.formation_panel.get_current_data_source()
            )

            # Get current selections and formation from away team panel
            # Note: on_formation_data_changed in team_panel.py already saves selections BEFORE clearing the table
            # So if the table is already cleared (empty selections), don't overwrite the saved selections
            if hasattr(self.away_team_panel, "player_table"):
                away_selections = self.away_team_panel.player_table.get_selected_rows()
                if away_data_source == "Team A":
                    away_formation = getattr(
                        self.away_team_panel,
                        "team_a_formation",
                        TeamConstants.SELECT_FORMATION,
                    )
                else:
                    away_formation = getattr(
                        self.away_team_panel,
                        "team_b_formation",
                        TeamConstants.SELECT_FORMATION,
                    )

                # Only save if selections are not empty OR if the pool for this data source is already empty
                # This prevents overwriting saved selections with empty set after table is cleared
                if away_selections:
                    # Selections exist, save them
                    if away_data_source == "Team A":
                        self.a_selected_rows = away_selections.copy()
                        self.pool_a_formation = away_formation
                    else:
                        self.b_selected_rows = away_selections.copy()
                        self.pool_b_formation = away_formation
                elif away_data_source == "Team A" and not self.a_selected_rows:
                    # Selections are empty AND pool is empty - preserve empty state
                    self.a_selected_rows = away_selections.copy()
                    self.pool_a_formation = away_formation
                elif away_data_source == "Team B" and not self.b_selected_rows:
                    # Selections are empty AND pool is empty - preserve empty state
                    self.b_selected_rows = away_selections.copy()
                    self.pool_b_formation = away_formation
                # Otherwise, selections are empty but pool has saved selections - don't overwrite

        except Exception:
            pass

    def create_match(self):
        """Create a new match with current data"""
        try:
            match_data = self.get_match_data()

            # Validate match data
            validation_errors = self.validate_match_data(match_data)
            if validation_errors:
                error_msg = "Please fix the following errors:\n\n" + "\n".join(
                    validation_errors
                )
                QMessageBox.warning(self, "Validation Error", error_msg)
                return

            # Show progress dialog
            progress = QProgressDialog("Creating match...", "Cancel", 0, 100, self)
            progress.setMinimumWidth(420)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Simulate match creation process
            QTimer.singleShot(100, lambda: progress.setValue(25))
            QTimer.singleShot(200, lambda: progress.setValue(50))
            QTimer.singleShot(300, lambda: progress.setValue(75))
            QTimer.singleShot(400, lambda: progress.setValue(100))

            # Create match using backend service
            QTimer.singleShot(
                500, lambda: self._finish_match_creation(match_data, progress)
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create match: {str(e)}")

    def _finish_match_creation(self, match_data: dict, progress: QProgressDialog):
        """Finish the match creation process"""
        try:
            # Here you would typically save to backend or database
            # For now, we'll just emit the signal
            match_id = f"match_{self.get_match_number()}_{hash(str(match_data))}"
            self.current_match_id = match_id

            progress.close()

            # Emit match created signal
            self.match_created.emit(match_id)

            # CRITICAL: Emit match_data_changed signal with complete data so Play On and Subs/Penalty tabs become operational
            # This ensures both tabs receive the match data with playing 11 and substitutions
            match_data["match_id"] = match_id
            match_data["status"] = "created"  # Match is now created
            self.match_data_changed.emit(match_data)

            try:
                sync_match_snapshot(match_id, match_data)
            except Exception as exc:
                print(f"[MatchSetupTab] Backend sync failed: {exc}")

            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Match #{self.get_match_number()} created successfully!\n\nPlay On and Subs & Penalty tabs are now operational.",
            )

        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self, "Error", f"Failed to finish match creation: {str(e)}"
            )

    def validate_match_data(self, match_data: dict) -> list:
        """Validate match data and return list of errors"""
        errors = []

        try:
            # Validate home team
            home_team = match_data.get("home_team", {})
            if not home_team.get("name"):
                errors.append("Home team name is required")

            # Validate away team
            away_team = match_data.get("away_team", {})
            if not away_team.get("name"):
                errors.append("Away team name is required")

            # Validate officials
            officials = match_data.get("officials", {})
            if not officials.get("referee"):
                errors.append("Referee is required")

            # Validate team formations
            if home_team.get("formation") == "Select Formation":
                errors.append("Home team formation must be selected")

            if away_team.get("formation") == "Select Formation":
                errors.append("Away team formation must be selected")

            # Validate player counts - check playing_11 first, then fall back to selected flag
            home_playing_11 = home_team.get("playing_11", [])
            if not home_playing_11:
                # Fallback: check selected flag in players array
                home_players = home_team.get("players", [])
                home_playing_11 = [p for p in home_players if p.get("selected", False)]

            if len(home_playing_11) != 11:
                errors.append(
                    f"Home team must have exactly 11 players selected (playing 11). Current: {len(home_playing_11)}"
                )

            away_playing_11 = away_team.get("playing_11", [])
            if not away_playing_11:
                # Fallback: check selected flag in players array
                away_players = away_team.get("players", [])
                away_playing_11 = [p for p in away_players if p.get("selected", False)]

            if len(away_playing_11) != 11:
                errors.append(
                    f"Away team must have exactly 11 players selected (playing 11). Current: {len(away_playing_11)}"
                )

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def load_match_data(self, match_data: dict):
        """Load match data into the UI components"""
        try:
            # Load match number
            if "match_number" in match_data:
                self.set_match_number(match_data["match_number"], emit_change=False)

            # Load team data
            if "home_team" in match_data:
                self.home_team_panel.load_team_data(match_data["home_team"])

            if "away_team" in match_data:
                self.away_team_panel.load_team_data(match_data["away_team"])

            # Load officials data
            if "officials" in match_data:
                self.officials_tab.load_officials_data(match_data["officials"])

        except Exception:
            pass

    def get_tab_style(self) -> str:
        """Get styling for the tab widget"""
        return """
            QTabWidget::pane {
                border: 1px solid #4b5563;
                border-radius: 8px;
                background: #1f2937;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
        """

    def get_tab_button_style(self, active: bool) -> str:
        """Get styling for tab buttons"""
        if active:
            return """
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #3b82f6, stop:1 #1d4ed8);
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-size: 14px;
                            font-weight: 600;
                            min-width: 100px;
                        }
                        QPushButton:hover {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2563eb, stop:1 #1e40af);
                        }
                    """
        else:
            return """
                QPushButton {
                    background: #374151;
                    color: #d1d5db;
                    border: 1px solid #4b5563;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background: #4b5563;
                    color: white;
                }
            """

    def get_create_button_style(self) -> str:
        """Get styling for the create match button"""
        return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                    color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 120px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #065f46);
                }
        """

    def get_match_number(self) -> int:
        """Return the current match number from the custom input."""
        try:
            value = int(self.match_input.text().strip())
        except (ValueError, AttributeError):
            value = 1
        return max(0, min(1000, value))

    def set_match_number(self, value: int, emit_change: bool = True):
        """Update the match number input and optionally emit data-changed."""
        try:
            numeric_value = int(value)
        except (ValueError, TypeError):
            numeric_value = 1
        numeric_value = max(0, min(1000, numeric_value))
        new_text = str(numeric_value)
        if self.match_input.text() != new_text:
            self.match_input.blockSignals(True)
            self.match_input.setText(new_text)
            self.match_input.blockSignals(False)
        if emit_change:
            self.on_data_changed()

    def increment_match_number(self):
        """Increment match number"""
        new_value = min(self.get_match_number() + 1, 1000)
        self.set_match_number(new_value)

    def decrement_match_number(self):
        """Decrement match number"""
        new_value = max(self.get_match_number() - 1, 0)
        self.set_match_number(new_value)

    def on_match_number_changed(self):
        """Handle manual match number input"""
        value = self.get_match_number()
        self.set_match_number(value)
