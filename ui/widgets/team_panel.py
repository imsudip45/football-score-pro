"""
Team Panel Widget for Football Score Pro 2.0
Based on the old app structure but integrated with new backend architecture
"""

import copy
import traceback
from typing import Any, Dict, Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.constants import DataKeys, TeamConstants

from ..backend_service import BackendService
from .content_panel import ContentPanel
from .control_panel import ControlPanel
from .formation_panel import FormationPanel
from .info_panel import InfoPanel
from .player_table import PlayerTable


class TeamPanel(QWidget):
    """Panel for managing team data and players"""

    # Signals
    data_changed = Signal()

    def __init__(self, team_name: str, backend_service: BackendService, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.backend_service = backend_service
        self.team_data = {}
        self.team_a_data = {}  # Store Team A data
        self.team_b_data = {}  # Store Team B data
        self.current_data_source = TeamConstants.TEAM_A  # Track current data source
        self.loading_players = False
        self.team_a_formation = TeamConstants.SELECT_FORMATION  # Store Team A formation
        self.team_b_formation = TeamConstants.SELECT_FORMATION  # Store Team B formation
        self.syncing = False  # Flag to prevent infinite sync loops
        self.restoring_selections = (
            False  # Flag to prevent saving during selection restoration
        )

        # Per-team primary color state
        self.team_a_color_1 = TeamConstants.DEFAULT_COLOR
        self.team_b_color_1 = TeamConstants.DEFAULT_COLOR

        # Per-team kit image filenames from JSON
        self.team_a_kit_image = None
        self.team_b_kit_image = None

        # Game_Setting.py style state management
        self.team_a_state = {
            DataKeys.FORMATION: TeamConstants.SELECT_FORMATION,
            DataKeys.POSITIONS: {},
        }
        self.team_b_state = {
            DataKeys.FORMATION: TeamConstants.SELECT_FORMATION,
            DataKeys.POSITIONS: {},
        }

        # Player selection tracking (like Game_Setting.py) - separate for Team A and Team B
        self.team_a_selected_rows = set()  # Track selected player rows for Team A
        self.team_b_selected_rows = set()  # Track selected player rows for Team B
        self.team_a_selected_count = 0
        self.team_b_selected_count = 0

        # Player data for ContentPanel - separate for Team A and Team B
        self.team_a_field_labels = {}  # row -> player_data mapping for Team A
        self.team_b_field_labels = {}  # row -> player_data mapping for Team B
        self.setup_ui()
        self.connect_signals()
        self.initialize_formation_labels()

    def setup_ui(self):
        """Setup the team panel UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left panel (formation and players)
        left_panel = self.create_left_panel()
        layout.addWidget(left_panel)

        # Right panel (info, content, controls)
        right_panel = self.create_right_panel()
        layout.addWidget(right_panel)

        # Ensure predictable layout proportions: left narrower, right wider
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)

    def create_left_panel(self):
        """Create left panel with formation and player table"""
        left_widget = QFrame()
        left_widget.setStyleSheet(self.get_panel_style("left"))
        # Fix the width so both Home and Away tabs reserve identical space
        left_widget.setMinimumWidth(780)
        left_widget.setMaximumWidth(780)

        layout = QVBoxLayout(left_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 5, 10, 5)

        # Formation section
        self.formation_panel = FormationPanel(self.team_name, self)
        self.formation_panel.data_changed.connect(self.on_formation_data_changed)
        layout.addWidget(self.formation_panel)

        # Player table
        self.player_table = PlayerTable(self.team_name, self)
        self.player_table.selection_changed.connect(self.on_selection_changed)
        layout.addWidget(self.player_table)

        # Add empty rows to start
        self.player_table.add_empty_rows(25)

        return left_widget

    @staticmethod
    def _derive_short_name(team_dict: Dict[str, Any], default: str) -> str:
        if not team_dict:
            return default
        short = team_dict.get(DataKeys.SHORT_NAME)
        if short:
            return short
        name_source = team_dict.get(DataKeys.FULL_NAME) or team_dict.get(DataKeys.NAME)
        if name_source:
            letters = "".join(ch for ch in name_source if ch.isalnum())
            if letters:
                return letters[:4].upper()
        return default

    def update_radio_short_names(
        self, team_a_data: Dict[str, Any], team_b_data: Dict[str, Any]
    ):
        """Update formation panel radio texts for both teams."""
        try:
            team_a_short = self._derive_short_name(team_a_data, TeamConstants.TEAM_A)
            team_b_short = self._derive_short_name(team_b_data, TeamConstants.TEAM_B)
            if hasattr(self, "formation_panel"):
                formation_panel = self.formation_panel
                if hasattr(formation_panel, "update_radio_texts"):
                    formation_panel.update_radio_texts(team_a_short, team_b_short)
                else:
                    if hasattr(formation_panel, "update_team_a_radio_text"):
                        formation_panel.update_team_a_radio_text(team_a_short)
                    if hasattr(formation_panel, "update_team_b_radio_text"):
                        formation_panel.update_team_b_radio_text(team_b_short)
        except Exception:
            pass

    def refresh_formation_labels(self):
        """Ensure formation labels reflect current Team A/B formations."""
        try:
            if not hasattr(self, "formation_panel"):
                return
            # Prefer global pool values so both panels stay in sync
            match_setup_tab = self.parent()
            while match_setup_tab and not hasattr(match_setup_tab, "pool_a_formation"):
                match_setup_tab = match_setup_tab.parent()

            formation_panel = self.formation_panel
            formation_a = None
            formation_b = None

            if match_setup_tab:
                formation_a = getattr(match_setup_tab, "pool_a_formation", None)
                formation_b = getattr(match_setup_tab, "pool_b_formation", None)

            formation_a = (
                formation_a
                or getattr(self, "team_a_formation", None)
                or (
                    getattr(self, "team_a_data", {}).get(DataKeys.FORMATION)
                    if getattr(self, "team_a_data", None)
                    else None
                )
                or TeamConstants.SELECT_FORMATION
            )
            formation_b = (
                formation_b
                or getattr(self, "team_b_formation", None)
                or (
                    getattr(self, "team_b_data", {}).get(DataKeys.FORMATION)
                    if getattr(self, "team_b_data", None)
                    else None
                )
                or TeamConstants.SELECT_FORMATION
            )

            if hasattr(formation_panel, "update_team_a_formation"):
                formation_panel.update_team_a_formation(formation_a)
            if hasattr(formation_panel, "update_team_b_formation"):
                formation_panel.update_team_b_formation(formation_b)
        except Exception:
            pass

    def create_right_panel(self):
        """Create right panel with info, content, and controls"""
        right_widget = QFrame()
        right_widget.setStyleSheet(self.get_panel_style("right"))

        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Info panel
        self.info_panel = InfoPanel(self.team_name, self)
        layout.addWidget(self.info_panel)

        # Horizontal layout for content and controls
        content_layout = QHBoxLayout()

        # Content area (field display)
        self.content_panel = ContentPanel(self.team_name, self)
        self.content_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout.addWidget(self.content_panel)

        # Control panel - now using ControlPanel widget
        self.control_panel = ControlPanel(self.team_name, self)
        self.control_panel.setMaximumWidth(160)
        # Connect signals from control panel
        self.control_panel.formation_changed.connect(self.on_formation_changed)
        self.control_panel.kit_changed.connect(self.on_kit_changed)
        self.control_panel.color_changed.connect(self.on_color_changed)
        self.control_panel.data_changed.connect(self.data_changed.emit)
        content_layout.addWidget(self.control_panel)

        layout.addLayout(content_layout)

        return right_widget

    # removed backwards compatibility code of here

    def connect_signals(self):
        """Connect internal signals"""
        # Connect formation applied signal from content panel
        if hasattr(self, "content_panel"):
            self.content_panel.formation_applied.connect(self.on_formation_applied)

        # Connect player selection signal from player table
        if hasattr(self, "player_table"):
            self.player_table.selection_changed.connect(self.handle_player_selection)

        # Connect reset button
        if hasattr(self, "info_panel") and self.info_panel.reset_button:
            self.info_panel.reset_button.clicked.connect(self.reset_team_data)

    def initialize_formation_labels(self):
        """Initialize formation labels with default values"""
        try:
            if hasattr(self, "formation_panel"):
                self.formation_panel.update_team_a_formation(self.team_a_formation)
                self.formation_panel.update_team_b_formation(self.team_b_formation)
        except Exception:
            pass

    def get_team_data(self) -> Dict[str, Any]:
        """Get current team data from UI with playing 11 and substitutions"""
        try:
            # Get current team data source
            current_data = (
                self.team_a_data
                if self.current_data_source == TeamConstants.TEAM_A
                else self.team_b_data
            )

            # Get all players from the player table and mark selected/unselected
            all_players = []
            selected_players = []  # Playing 11
            substitution_players = []  # Unselected players

            if hasattr(self, "player_table"):
                selected_rows = self.player_table.get_selected_rows()

                # Get original players data from current team data for additional fields
                original_players = current_data.get(DataKeys.PLAYERS, [])

                for row in range(self.player_table.rowCount()):
                    num_item = self.player_table.item(row, 0)
                    name_item = self.player_table.item(row, 1)
                    id_item = self.player_table.item(row, 2)
                    position_item = self.player_table.item(row, 3)

                    if num_item and name_item and num_item.text().strip():
                        jersey_no = num_item.text().strip()
                        name = name_item.text().strip()
                        player_id = id_item.text().strip() if id_item else ""
                        position = position_item.text().strip() if position_item else ""

                        # Try to find original player data to preserve all fields
                        original_player = None
                        for orig_p in original_players:
                            orig_jersey = str(
                                orig_p.get(
                                    DataKeys.JERSEY_NUMBER,
                                    orig_p.get(DataKeys.JERSEY_NO, ""),
                                )
                            ).strip()
                            orig_name = str(
                                orig_p.get(
                                    DataKeys.NAME, orig_p.get(DataKeys.FULL_NAME, "")
                                )
                            ).strip()
                            if orig_jersey == jersey_no or orig_name == name:
                                original_player = orig_p
                                break

                        # Build player object with all fields for compatibility
                        player = {
                            DataKeys.JERSEY_NO: jersey_no,
                            DataKeys.JERSEY_NUMBER: jersey_no,  # For Play On tab compatibility
                            DataKeys.NAME: name,
                            DataKeys.FULL_NAME: name,  # For Play On tab compatibility
                            DataKeys.ID: player_id
                            or (
                                original_player.get(DataKeys.ID, "")
                                if original_player
                                else ""
                            ),
                            DataKeys.POSITION: position
                            or (
                                original_player.get(DataKeys.POSITION, "")
                                if original_player
                                else ""
                            ),
                            DataKeys.SELECTED: row
                            in selected_rows,  # True if in playing 11
                            DataKeys.IS_SUBSTITUTION: row
                            not in selected_rows,  # True if not selected
                        }

                        # Preserve any additional fields from original player data
                        if original_player:
                            for key, value in original_player.items():
                                if (
                                    key not in player
                                ):  # Don't overwrite fields we've already set
                                    player[key] = value

                        all_players.append(player)

                        if row in selected_rows:
                            selected_players.append(player)
                        else:
                            substitution_players.append(player)

            # Get basic team info
            team_data = {
                DataKeys.ID: current_data.get(DataKeys.ID, ""),
                DataKeys.NAME: current_data.get(DataKeys.NAME, ""),
                DataKeys.FULL_NAME: current_data.get(DataKeys.FULL_NAME, ""),
                DataKeys.SHORT_NAME: current_data.get(DataKeys.SHORT_NAME, ""),
                DataKeys.MANAGER: current_data.get(DataKeys.MANAGER, ""),
                DataKeys.HEAD_COACH: current_data.get(DataKeys.HEAD_COACH, ""),
                DataKeys.FORMATION: self.team_a_formation
                if self.current_data_source == TeamConstants.TEAM_A
                else self.team_b_formation,
                DataKeys.COLOR_1: self.control_panel.color_panel.color_1
                if hasattr(self, "control_panel") and self.control_panel.color_panel
                else TeamConstants.DEFAULT_COLOR,
                DataKeys.COLOR_2: self.control_panel.color_panel.color_2
                if hasattr(self, "control_panel") and self.control_panel.color_panel
                else TeamConstants.DEFAULT_COLOR,
                DataKeys.COLOR_MODE: self.control_panel.color_panel.color_mode
                if hasattr(self, "control_panel") and self.control_panel.color_panel
                else "single",
                DataKeys.LOGO: current_data.get(
                    DataKeys.LOGO
                ),  # Include logo from fixture
                DataKeys.LOGO_URL: current_data.get(
                    DataKeys.LOGO_URL
                ),  # Include logo_url as fallback
                DataKeys.KITS: copy.deepcopy(current_data.get(DataKeys.KITS, [])),
                "kit_index": getattr(self.control_panel, "current_kit_index", 0)
                if hasattr(self, "control_panel")
                else 0,
                DataKeys.PLAYERS: all_players,  # All players
                DataKeys.PLAYING_11: selected_players,  # Selected players (playing 11)
                DataKeys.SUBSTITUTIONS: substitution_players,  # Unselected players (substitutions)
            }

            return team_data

        except Exception as e:
            print(f"Error getting team data for {self.team_name}: {e}")
            import traceback

            traceback.print_exc()
            return {}

    def export_state(self) -> dict:
        """Serialize both Team A/B pools so autosave can restore full styling."""
        try:

            def _serialize_team(
                team_data: dict,
                formation: str,
                color: str,
                selected_rows: set,
                kit_image: Optional[str],
            ):
                data_copy = copy.deepcopy(team_data or {})
                if formation:
                    data_copy.setdefault(DataKeys.FORMATION, formation)
                if color:
                    data_copy.setdefault(DataKeys.COLOR_1, color)
                if kit_image:
                    data_copy.setdefault(DataKeys.KIT_IMAGE, kit_image)
                data_copy.setdefault(DataKeys.KITS, team_data.get(DataKeys.KITS, []))
                data_copy.setdefault("kit_index", team_data.get("kit_index", 0))
                return {
                    "data": data_copy,
                    "formation": formation,
                    "color_1": color,
                    "selected_rows": sorted(selected_rows or []),
                    "kit_image": kit_image,
                }

            state = {
                "current_data_source": self.current_data_source,
                "team_a": _serialize_team(
                    getattr(self, "team_a_data", {}),
                    getattr(self, "team_a_formation", TeamConstants.SELECT_FORMATION),
                    getattr(self, "team_a_color_1", TeamConstants.DEFAULT_COLOR),
                    getattr(self, "team_a_selected_rows", set()),
                    getattr(self, "team_a_kit_image", None),
                ),
                "team_b": _serialize_team(
                    getattr(self, "team_b_data", {}),
                    getattr(self, "team_b_formation", TeamConstants.SELECT_FORMATION),
                    getattr(self, "team_b_color_1", TeamConstants.DEFAULT_COLOR),
                    getattr(self, "team_b_selected_rows", set()),
                    getattr(self, "team_b_kit_image", None),
                ),
            }
            return state
        except Exception as exc:
            print(f"Error exporting team panel state: {exc}")
            return {}

    def load_state(self, state: dict):
        """Restore TeamPanel pools, colors, kits, and selections from autosave."""
        try:
            if not state:
                return

            def _restore_team(slot_state: dict, is_team_a: bool):
                data = copy.deepcopy(slot_state.get("data") or {})
                formation = slot_state.get("formation", TeamConstants.SELECT_FORMATION)
                color = slot_state.get("color_1", TeamConstants.DEFAULT_COLOR)
                kit_image = slot_state.get("kit_image")
                kit_index = data.get("kit_index", 0)
                selected_rows = set(slot_state.get("selected_rows", []))

                if is_team_a:
                    self.team_a_data = data
                    self.team_a_formation = formation
                    self.team_a_color_1 = color
                    self.team_a_kit_image = kit_image
                    self.team_a_selected_rows = selected_rows
                    self.team_a_data["kit_index"] = kit_index
                else:
                    self.team_b_data = data
                    self.team_b_formation = formation
                    self.team_b_color_1 = color
                    self.team_b_kit_image = kit_image
                    self.team_b_selected_rows = selected_rows
                    self.team_b_data["kit_index"] = kit_index

            _restore_team(state.get("team_a", {}), is_team_a=True)
            _restore_team(state.get("team_b", {}), is_team_a=False)

            desired_source = state.get("current_data_source", TeamConstants.TEAM_A)
            if desired_source not in (TeamConstants.TEAM_A, TeamConstants.TEAM_B):
                desired_source = TeamConstants.TEAM_A
            self.current_data_source = desired_source

            # Re-render the currently selected pool so UI reflects restored styling.
            if desired_source == TeamConstants.TEAM_B and self.team_b_data:
                self.set_team_data(
                    self.team_b_data,
                    TeamConstants.TEAM_B,
                    persist_color=False,
                    preserve_formation=True,
                )
            elif self.team_a_data:
                self.set_team_data(
                    self.team_a_data,
                    TeamConstants.TEAM_A,
                    persist_color=False,
                    preserve_formation=True,
                )

            self.refresh_formation_labels()
        except Exception as exc:
            print(f"Error loading team panel state: {exc}")

    def set_team_data(
        self,
        team_data: Dict[str, Any],
        data_source: str = None,
        persist_color: bool = True,
        preserve_formation: bool = False,
    ):
        """Set team data into the UI.
        persist_color controls whether incoming team_data["color_1"] overwrites stored per-team color.
        """
        try:
            # Skip if we're in the middle of syncing to prevent infinite loops
            if self.syncing:
                return

            self.loading_players = True

            # Determine which team slot to use
            if data_source is None:
                data_source = self.current_data_source

            # Store data in appropriate slot
            if data_source == TeamConstants.TEAM_A:
                self.team_a_data = team_data.copy()
                self.team_data = self.team_a_data
                # Persist Team A color only if requested
                if persist_color and (DataKeys.COLOR_1 in team_data):
                    self.team_a_color_1 = team_data.get(
                        DataKeys.COLOR_1, self.team_a_color_1
                    )
                # Store kit image filename from JSON
                if DataKeys.KIT_IMAGE in team_data:
                    self.team_a_kit_image = team_data.get(DataKeys.KIT_IMAGE)
            else:
                self.team_b_data = team_data.copy()
                self.team_data = self.team_b_data
                if not preserve_formation:
                    self.team_b_formation = team_data.get(
                        DataKeys.FORMATION, self.team_b_formation
                    )
                # Persist Team B color only if requested
                if persist_color and (DataKeys.COLOR_1 in team_data):
                    self.team_b_color_1 = team_data.get(
                        DataKeys.COLOR_1, self.team_b_color_1
                    )
                # Store kit image filename from JSON
                if DataKeys.KIT_IMAGE in team_data:
                    self.team_b_kit_image = team_data.get(DataKeys.KIT_IMAGE)

            # Update current data source
            self.current_data_source = data_source

            # Update formation panel to reflect current data source
            self.formation_panel.set_data_source_without_emit(data_source)

            # Update radio button text with team short names
            if hasattr(self, "formation_panel"):
                if data_source == TeamConstants.TEAM_A:
                    team_a_short_name = self._derive_short_name(
                        self.team_a_data, TeamConstants.TEAM_A
                    )
                    team_b_short_name = self._derive_short_name(
                        getattr(self, "team_b_data", {}), TeamConstants.TEAM_B
                    )
                else:
                    team_a_short_name = self._derive_short_name(
                        getattr(self, "team_a_data", {}), TeamConstants.TEAM_A
                    )
                    team_b_short_name = self._derive_short_name(
                        self.team_b_data, TeamConstants.TEAM_B
                    )

                formation_panel = self.formation_panel
                if hasattr(formation_panel, "update_radio_texts"):
                    formation_panel.update_radio_texts(
                        team_a_short_name, team_b_short_name
                    )
                else:
                    if hasattr(formation_panel, "update_team_a_radio_text"):
                        formation_panel.update_team_a_radio_text(team_a_short_name)
                    if hasattr(formation_panel, "update_team_b_radio_text"):
                        formation_panel.update_team_b_radio_text(team_b_short_name)

            # Block signals to prevent infinite loops
            formation_input = getattr(self.control_panel, "formation_input", None)
            if formation_input:
                formation_input.blockSignals(True)
            self.control_panel.color_panel.blockSignals(True)

            # Update formation selector
            formation = team_data.get(DataKeys.FORMATION, "Select Formation")
            if formation_input:
                formation_input.setText(
                    formation if formation != "Select Formation" else ""
                )

            # Update color panel - show stored per-team color on internal switches
            # Prefer global pools from parent if available, to keep both panels in sync
            match_setup_tab = self.parent()
            while match_setup_tab and not hasattr(match_setup_tab, "pool_a_color_1"):
                match_setup_tab = match_setup_tab.parent()
            if data_source == TeamConstants.TEAM_A:
                color1_stored = (
                    getattr(match_setup_tab, "pool_a_color_1", self.team_a_color_1)
                    if match_setup_tab
                    else self.team_a_color_1
                )
                # Sync local store with global
                self.team_a_color_1 = color1_stored
            else:
                color1_stored = (
                    getattr(match_setup_tab, "pool_b_color_1", self.team_b_color_1)
                    if match_setup_tab
                    else self.team_b_color_1
                )
                # Sync local store with global
                self.team_b_color_1 = color1_stored

            if persist_color:
                color1_display = team_data.get(DataKeys.COLOR_1, color1_stored)
            else:
                color1_display = color1_stored

            self.control_panel.color_panel.update_colors(
                color1_display,
                team_data.get(DataKeys.COLOR_2, TeamConstants.DEFAULT_COLOR),
                team_data.get(DataKeys.COLOR_MODE, "single"),
            )

            # Ensure field reflects stored color for current data source
            if hasattr(self, "content_panel"):
                color = (
                    self.team_a_color_1
                    if data_source == TeamConstants.TEAM_A
                    else self.team_b_color_1
                )
                self.content_panel.update_team_color(color)

            # Update info panel
            self.info_panel.update_display(team_data)

            # Update manager label on the field
            if hasattr(self, "content_panel"):
                manager_text = (
                    team_data.get(DataKeys.MANAGER)
                    or team_data.get(DataKeys.HEAD_COACH)
                    or team_data.get(DataKeys.COACH)
                    or "Not Set"
                )
                self.content_panel.update_manager_label(manager_text)

            # Update player table
            self.update_player_table(team_data)

            # Re-apply stored selections for this data source so field updates immediately
            stored_rows = (
                sorted(self.team_a_selected_rows)
                if data_source == TeamConstants.TEAM_A
                else sorted(self.team_b_selected_rows)
            )
            if hasattr(self, "player_table"):
                self.restoring_selections = True
                try:
                    self.player_table.apply_selected_rows(stored_rows)
                finally:
                    self.restoring_selections = False
                if hasattr(self, "info_panel"):
                    self.info_panel.update_selected_count(len(stored_rows))

            # Update kit button and load kit image if available (from JSON or dropdown)
            if hasattr(self, "control_panel") and self.control_panel.kit_button:
                # Check if kits array exists in team_data
                kits = team_data.get(DataKeys.KITS, [])
                if kits and len(kits) > 0:
                    # Enable button
                    self.control_panel.kit_button.setEnabled(True)

                    # Load kit from pool for the current data source
                    match_setup_tab = self.parent()
                    while match_setup_tab and not hasattr(
                        match_setup_tab, "pool_a_kit_index"
                    ):
                        match_setup_tab = match_setup_tab.parent()

                    if match_setup_tab:
                        # Get kit index from appropriate pool
                        if data_source == TeamConstants.TEAM_A:
                            kit_index = getattr(match_setup_tab, "pool_a_kit_index", 0)
                        else:
                            kit_index = getattr(match_setup_tab, "pool_b_kit_index", 0)

                        # Ensure kit_index is within valid range
                        if kit_index >= len(self.control_panel.kit_options):
                            kit_index = 0

                        # Set kit index and button text
                        self.control_panel.current_kit_index = kit_index
                        kit_text = self.control_panel.kit_options[kit_index]
                        self.control_panel.kit_button.setText(kit_text)
                        print(
                            f"Loaded kit index {kit_index} ({kit_text}) from {data_source} pool"
                        )

                        # Load the kit image (this will trigger on_kit_changed, but we'll mark it as loading)
                        # We need to temporarily block the save to pool
                        self.control_panel.load_jersey_image()  # Loads the kit and updates colors!
                    else:
                        # Fallback to Home Kit if pool not found
                        if "Home Kit" in self.control_panel.kit_options:
                            self.control_panel.current_kit_index = (
                                self.control_panel.kit_options.index("Home Kit")
                            )
                            self.control_panel.kit_button.setText("Home Kit")
                            self.control_panel.load_jersey_image()
                else:
                    # No kits available, keep button disabled
                    self.control_panel.kit_button.setEnabled(False)
                    self.control_panel.kit_button.setText("No kits loaded")
                    self.control_panel.image_label.clear()  # Clear image if no kits

            # Schedule formation application after player table is fully populated
            if hasattr(self, "content_panel"):
                # Use QTimer to apply formation after player table has been populated
                QTimer.singleShot(
                    100,
                    lambda: self._apply_formation_after_load(data_source, team_data),
                )

            # Keep formation labels in sync with stored team data
            self.refresh_formation_labels()

            # Unblock signals
            if formation_input := getattr(self.control_panel, "formation_input", None):
                formation_input.blockSignals(False)
            self.control_panel.color_panel.blockSignals(False)

            self.loading_players = False
            self.data_changed.emit()

        except Exception:
            self.loading_players = False

    def update_player_table(self, team_data: Dict[str, Any]):
        """Update player table with team data"""
        try:
            players = team_data.get(DataKeys.PLAYERS, [])

            # Convert players to the format expected by PlayerTable
            players_data = []
            for player in players:
                player_dict = {
                    DataKeys.JERSEY_NO: player.get(
                        DataKeys.JERSEY_NUMBER, player.get(DataKeys.JERSEY_NO, 0)
                    ),
                    DataKeys.FULL_NAME: player.get(
                        DataKeys.NAME, player.get(DataKeys.FULL_NAME, "")
                    ),
                    DataKeys.ID: player.get(DataKeys.ID, ""),
                    DataKeys.POSITION: player.get(DataKeys.POSITION, ""),
                    DataKeys.SELECTED: player.get(DataKeys.SELECTED, False),
                }
                players_data.append(player_dict)

            # Update player table
            self.player_table.populate_players(players_data)

        except Exception:
            pass

    def get_all_players(self) -> list:
        """Get all players from the table"""
        players = []
        for row in range(self.player_table.rowCount()):
            # Get basic player data
            num_item = self.player_table.item(row, 0)
            name_item = self.player_table.item(row, 1)
            id_item = self.player_table.item(row, 2)
            position_item = self.player_table.item(row, 3)

            # Skip empty rows
            if not any(
                [
                    num_item and num_item.text().strip(),
                    name_item and name_item.text().strip(),
                ]
            ):
                continue

            # Get selection status
            selected = self.player_table.is_row_selected(row)

            player = {
                DataKeys.JERSEY_NUMBER: num_item.text().strip() if num_item else "",
                DataKeys.NAME: name_item.text().strip() if name_item else "",
                DataKeys.ID: id_item.text().strip() if id_item else "",
                DataKeys.POSITION: position_item.text().strip()
                if position_item
                else "",
                DataKeys.SELECTED: selected,
            }

            players.append(player)

        return players

    def get_selected_players(self) -> list:
        """Get only selected players from the table"""
        return self.player_table.get_selected_players()

    def on_formation_data_changed(self):
        """Handle formation data changes from formation panel"""
        try:
            # Get the current data source from formation panel (NEW value)
            new_data_source = self.formation_panel.get_current_data_source()

            # Get OLD data source (what we're leaving)
            old_data_source = self.current_data_source

            # Find MatchSetupTab by traversing up the widget hierarchy
            parent = self.parent()
            match_setup_tab = None
            while parent:
                if hasattr(parent, "a_selected_rows"):
                    match_setup_tab = parent
                    break
                parent = parent.parent()

            # CRITICAL: Save current selections BEFORE set_team_data() clears them
            if hasattr(self, "player_table") and not self.restoring_selections:
                current_selections = self.player_table.get_selected_rows()
                if self.current_data_source == TeamConstants.TEAM_A:
                    current_formation = getattr(
                        self, "team_a_formation", TeamConstants.SELECT_FORMATION
                    )
                else:
                    current_formation = getattr(
                        self, "team_b_formation", TeamConstants.SELECT_FORMATION
                    )

                if match_setup_tab:
                    # Only save if selections are not empty OR if the pool is already empty (to preserve empty state when explicitly clearing)
                    # This prevents overwriting saved selections with empty ones when the table is cleared during team switches
                    if old_data_source == TeamConstants.TEAM_A:
                        if current_selections or not match_setup_tab.a_selected_rows:
                            match_setup_tab.a_selected_rows = current_selections.copy()
                            match_setup_tab.pool_a_formation = current_formation
                    else:
                        if current_selections or not match_setup_tab.b_selected_rows:
                            match_setup_tab.b_selected_rows = current_selections.copy()
                            match_setup_tab.pool_b_formation = current_formation

            # If we have a MatchSetupTab parent, let it handle the data loading and state orchestration
            # to prevent race conditions and double-saves where the global pool gets overwritten with empty data.
            # MatchSetupTab connects to the same data_changed signal and will call set_team_data.
            if match_setup_tab:
                return

            # Update our current data source
            self.current_data_source = new_data_source

            # Load the appropriate team data (this will clear selections)
            if new_data_source == TeamConstants.TEAM_A and self.team_a_data:
                self.set_team_data(
                    self.team_a_data, TeamConstants.TEAM_A, persist_color=False
                )
            elif new_data_source == TeamConstants.TEAM_B and self.team_b_data:
                self.set_team_data(
                    self.team_b_data, TeamConstants.TEAM_B, persist_color=False
                )

            # Immediately re-apply the current formation using current selections
            self.apply_current_formation()

        except Exception:
            pass

    def switch_team_data_source(self, data_source: str):
        """Switch between Team A and Team B data sources"""
        try:
            # Update current data source
            self.current_data_source = data_source

            # Update formation panel
            self.formation_panel.set_data_source_without_emit(data_source)

            # Update formation textbox to show the correct formation for the selected team
            formation_input = getattr(self.control_panel, "formation_input", None)
            if formation_input:
                formation_input.blockSignals(True)
                if data_source == TeamConstants.TEAM_A:
                    formation_input.setText(
                        self.team_a_formation
                        if self.team_a_formation != "Select Formation"
                        else ""
                    )
                else:
                    formation_input.setText(
                        self.team_b_formation
                        if self.team_b_formation != "Select Formation"
                        else ""
                    )
                formation_input.blockSignals(False)

                # Load the appropriate team data
                if data_source == TeamConstants.TEAM_A and self.team_a_data:
                    self.set_team_data(
                        self.team_a_data,
                        TeamConstants.TEAM_A,
                        persist_color=False,
                        preserve_formation=True,
                    )
                elif data_source == TeamConstants.TEAM_B and self.team_b_data:
                    self.set_team_data(
                        self.team_b_data,
                        TeamConstants.TEAM_B,
                        persist_color=False,
                        preserve_formation=True,
                    )
            else:
                # Clear the field if no team data is available
                if hasattr(self, "content_panel"):
                    self.content_panel.clear_players()

                # Immediately re-apply the current formation using current selections
                self.apply_current_formation()

                # Ensure formation labels reflect the latest stored formations
                self.refresh_formation_labels()

                # Ensure field color reflects the stored color for this data source
                if hasattr(self, "content_panel"):
                    color = (
                        self.team_a_color_1
                        if data_source == TeamConstants.TEAM_A
                        else self.team_b_color_1
                    )
                    self.content_panel.update_team_color(color)

        except Exception as e:
            print(f"Error switching team data source: {e}")
            traceback.print_exc()

    def on_selection_changed(self, selected_rows: list):
        """Handle player selection changes"""
        try:
            print(
                f"Player selection changed in {self.team_name}: {len(selected_rows)} players selected"
            )
            print(f"Selected rows: {selected_rows}")
            print(f"Current data source: {self.current_data_source}")

            # Update the appropriate selection state
            if self.current_data_source == TeamConstants.TEAM_A:
                self.team_a_selected_rows = set(selected_rows)
                self.team_a_selected_count = len(selected_rows)
                # Also update sibling panel if it exists and is showing same data
                sibling_panel = self._find_sibling_panel()
                if (
                    sibling_panel
                    and getattr(sibling_panel, "current_data_source", "")
                    == TeamConstants.TEAM_A
                ):
                    sibling_panel.team_a_selected_rows = set(selected_rows)
                    sibling_panel.team_a_selected_count = len(selected_rows)
                print(f"Updated Team A state: {self.team_a_selected_rows}")
            else:
                self.team_b_selected_rows = set(selected_rows)
                self.team_b_selected_count = len(selected_rows)
                # Also update sibling panel if it exists and is showing same data
                sibling_panel = self._find_sibling_panel()
                if (
                    sibling_panel
                    and getattr(sibling_panel, "current_data_source", "")
                    == TeamConstants.TEAM_B
                ):
                    sibling_panel.team_b_selected_rows = set(selected_rows)
                    sibling_panel.team_b_selected_count = len(selected_rows)
                print(f"Updated Team B state: {self.team_b_selected_rows}")

            # Update info panel
            if self.info_panel:
                self.info_panel.update_selected_count(len(selected_rows))

            # Determine the current formation text (defaults to Select Formation)
            current_formation = TeamConstants.SELECT_FORMATION
            formation_input = getattr(self.control_panel, "formation_input", None)
            if formation_input:
                text = formation_input.text().strip()
                if text:
                    current_formation = text

            # Update content panel with latest formation and selected players
            selected_players = self.get_selected_players()
            if self.content_panel:
                self.content_panel.update_formation(current_formation)
                self.content_panel.update_selected_players(
                    selected_players, self.current_data_source
                )
                if (
                    current_formation != TeamConstants.SELECT_FORMATION
                    and len(selected_rows) == 11
                ):
                    color = (
                        self.team_a_color_1
                        if self.current_data_source == TeamConstants.TEAM_A
                        else self.team_b_color_1
                    )
                    self.content_panel.update_team_color(color)

            # Save to global pools immediately when selections change
            if not self.restoring_selections:
                self.save_current_state_to_global_pools()
            print("Emitting data_changed signal")
            self.data_changed.emit()
            print("Data changed signal emitted")

        except Exception as ex:
            print(f"Error handling selection change: {ex}")
            traceback.print_exc()

    def handle_player_selection(self, selected_rows: list):
        """Handle player selection from player table"""
        try:
            print(f"Handling player selection: {selected_rows}")
            self.on_selection_changed(selected_rows)
        except Exception as e:
            print(f"Error handling player selection: {e}")

    def save_current_state_to_global_pools(self):
        """Save current state to global pools in MatchSetupTab"""
        try:
            # Find the MatchSetupTab by traversing up the widget hierarchy
            match_setup_tab = self.parent()
            while match_setup_tab and not hasattr(match_setup_tab, "a_selected_rows"):
                match_setup_tab = match_setup_tab.parent()

            if not match_setup_tab or not hasattr(match_setup_tab, "a_selected_rows"):
                return

            # Get current selections and formation
            current_selections = (
                self.player_table.get_selected_rows()
                if hasattr(self, "player_table")
                else set()
            )
            if self.current_data_source == TeamConstants.TEAM_A:
                current_formation = getattr(
                    self, "team_a_formation", TeamConstants.SELECT_FORMATION
                )
            else:
                current_formation = getattr(
                    self, "team_b_formation", TeamConstants.SELECT_FORMATION
                )

            # Determine which pool to save to based on current data source
            if self.current_data_source == TeamConstants.TEAM_A:
                # Only save if selections are not empty OR if the pool is already empty (to preserve empty state when explicitly clearing)
                # This prevents overwriting saved selections with empty ones when the table is cleared during team switches
                if current_selections or not match_setup_tab.a_selected_rows:
                    match_setup_tab.a_selected_rows = current_selections.copy()
                    match_setup_tab.pool_a_formation = current_formation
                    print(
                        f"Saved {self.team_name} selections to Team A pool: {len(current_selections)} rows"
                    )
            else:
                # Only save if selections are not empty OR if the pool is already empty (to preserve empty state when explicitly clearing)
                # This prevents overwriting saved selections with empty ones when the table is cleared during team switches
                if current_selections or not match_setup_tab.b_selected_rows:
                    match_setup_tab.b_selected_rows = current_selections.copy()
                    match_setup_tab.pool_b_formation = current_formation
                    print(
                        f"Saved {self.team_name} selections to Team B pool: {len(current_selections)} rows"
                    )

        except Exception:
            pass

    def apply_formation_to_draggable_labels(self, formation: str):
        """Apply formation to draggable labels on the field"""
        try:
            if hasattr(self, "content_panel"):
                self.content_panel.apply_formation(formation)
        except Exception as e:
            print(f"Error applying formation to draggable labels: {e}")

    def hide_all_field_labels(self):
        """Hide all field labels"""
        try:
            if hasattr(self, "content_panel"):
                self.content_panel.clear_players()
        except Exception as e:
            print(f"Error hiding field labels: {e}")

    def cycle_kit(self):
        """Cycle through kit options when button is clicked - delegates to control panel"""
        if hasattr(self, "control_panel") and self.control_panel:
            self.control_panel.cycle_kit()

    def on_kit_changed(self, kit_type: str):
        """Handle kit type changes - control panel handles loading, this just emits data_changed"""
        try:
            print(f"Kit changed to: {kit_type}")
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling kit change: {e}")
            traceback.print_exc()

    def on_formation_changed(self, formation: str):
        """Handle formation changes"""
        try:
            print(f"Formation changed to: {formation} in {self.team_name}")

            # Check if 11 players are selected
            selected_players = self.get_selected_players()
            if len(selected_players) != 11:
                # Show warning popup

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Formation Selection")
                msg.setText(
                    "Please select exactly 11 players before choosing a formation."
                )
                msg.setInformativeText(
                    f"Currently {len(selected_players)} players are selected. You need 11 players to apply a formation."
                )
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

                # Reset formation dropdown to previous value
                if self.current_data_source == "Team A":
                    previous_formation = self.team_a_formation
                else:
                    previous_formation = self.team_b_formation

                # Block signals to prevent recursion
                formation_input = getattr(self.control_panel, "formation_input", None)
                if formation_input:
                    formation_input.blockSignals(True)
                    if previous_formation == TeamConstants.SELECT_FORMATION:
                        formation_input.clear()
                    else:
                        formation_input.setText(previous_formation)
                    formation_input.blockSignals(False)

                print(
                    f"Formation change blocked - only {len(selected_players)} players selected"
                )
                return

            # Update the appropriate team state
            sibling_panel = None
            match_setup_tab = self.parent()
            while match_setup_tab and not hasattr(match_setup_tab, "home_team_panel"):
                match_setup_tab = match_setup_tab.parent()
            if match_setup_tab:
                if self is match_setup_tab.home_team_panel:
                    sibling_panel = getattr(match_setup_tab, "away_team_panel", None)
                elif self is match_setup_tab.away_team_panel:
                    sibling_panel = getattr(match_setup_tab, "home_team_panel", None)

            if self.current_data_source == "Team A":
                self.team_a_formation = formation
                if isinstance(getattr(self, "team_a_data", None), dict):
                    self.team_a_data[DataKeys.FORMATION] = formation
                self._update_match_setup_team_data_formation(
                    TeamConstants.TEAM_A, formation
                )
                # Update Team A formation label
                if hasattr(self, "formation_panel"):
                    self.formation_panel.update_team_a_formation(formation)
                if sibling_panel:
                    sibling_panel.team_a_formation = formation
                    sibling_panel.refresh_formation_labels()
            else:
                self.team_b_formation = formation
                if isinstance(getattr(self, "team_b_data", None), dict):
                    self.team_b_data[DataKeys.FORMATION] = formation
                self._update_match_setup_team_data_formation(
                    TeamConstants.TEAM_B, formation
                )
                # Update Team B formation label
                if hasattr(self, "formation_panel"):
                    self.formation_panel.update_team_b_formation(formation)
                if sibling_panel:
                    sibling_panel.team_b_formation = formation
                    sibling_panel.refresh_formation_labels()

            # Apply formation to the field display using the same logic as when selecting 11 players
            if hasattr(self, "content_panel"):
                # Use the same formation application logic as in on_selection_changed
                self.content_panel.update_formation(formation)
                self.content_panel.update_selected_players(
                    selected_players, self.current_data_source
                )
                print(
                    f"Applied formation {formation} to field display with {len(selected_players)} players"
                )

            # Save to global pools immediately
            self.save_current_state_to_global_pools()

            # Emit data changed signal
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling formation change: {e}")
            import traceback

            traceback.print_exc()

    def on_formation_applied(self, formation: str):
        """Handle formation applied signal from content panel"""
        try:
            if self.current_data_source == TeamConstants.TEAM_A:
                self.team_a_formation = formation
                if isinstance(getattr(self, "team_a_data", None), dict):
                    self.team_a_data[DataKeys.FORMATION] = formation
                self._update_match_setup_team_data_formation(
                    TeamConstants.TEAM_A, formation
                )
            else:
                self.team_b_formation = formation
                if isinstance(getattr(self, "team_b_data", None), dict):
                    self.team_b_data[DataKeys.FORMATION] = formation
                self._update_match_setup_team_data_formation(
                    TeamConstants.TEAM_B, formation
                )
        except Exception as e:
            print(f"Error handling formation applied: {e}")

    def on_color_changed(self):
        """Handle color changes"""
        try:
            print(f"Color changed in {self.team_name}")
            # Update content panel with new team color
            if hasattr(self, "content_panel"):
                current_source = (
                    self.formation_panel.get_current_data_source()
                    if hasattr(self, "formation_panel")
                    else self.current_data_source
                )
                new_color = self.control_panel.color_panel.color_1
                # Persist to the active team's stored color
                if current_source == "Team A":
                    self.team_a_color_1 = new_color
                else:
                    self.team_b_color_1 = new_color
                # Apply to this panel's field only
                self.content_panel.update_team_color(new_color)

                # Update global pools so the other panel stays in sync
                match_setup_tab = self.parent()
                while match_setup_tab and not hasattr(
                    match_setup_tab, "pool_a_color_1"
                ):
                    match_setup_tab = match_setup_tab.parent()
                if match_setup_tab:
                    if current_source == "Team A":
                        match_setup_tab.pool_a_color_1 = new_color
                    else:
                        match_setup_tab.pool_b_color_1 = new_color

                    # Propagate color to sibling panel if it is showing the same data source
                    sibling = None
                    if (
                        hasattr(match_setup_tab, "home_team_panel")
                        and match_setup_tab.home_team_panel is not self
                    ):
                        sibling = match_setup_tab.home_team_panel
                    if (
                        hasattr(match_setup_tab, "away_team_panel")
                        and match_setup_tab.away_team_panel is not self
                    ):
                        # Prefer away as sibling if home was self
                        sibling = sibling or match_setup_tab.away_team_panel
                    if sibling and hasattr(sibling, "content_panel"):
                        # If sibling shows the same data source, sync its local store and field color
                        if (
                            getattr(sibling, "current_data_source", "")
                            == current_source
                        ):
                            if current_source == "Team A":
                                sibling.team_a_color_1 = new_color
                            else:
                                sibling.team_b_color_1 = new_color
                            sibling.content_panel.update_team_color(new_color)
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling color change: {e}")

    def load_jersey_image(self):
        """Load and display jersey image - delegates to control panel"""
        if hasattr(self, "control_panel") and self.control_panel:
            self.control_panel.load_jersey_image()

    def load_team_data(self, team_data: dict, preserve_selections: bool = False):
        """Load team data into the panel"""
        try:
            print(
                f"Loading team data for {self.team_name}: {team_data.get('name', 'Unknown Team')}"
            )
            # set_team_data() will handle kit button update
            self.set_team_data(team_data)
        except Exception as ex:
            print(f"Error loading team data for {self.team_name}: {ex}")

    def clear_players(self):
        """Clear all players"""
        try:
            if self.player_table:
                self.player_table.clear_all()
                self.player_table.add_empty_rows(25)
            self.data_changed.emit()
        except Exception as e:
            print(f"Error clearing players for {self.team_name}: {e}")

    def validate(self) -> list:
        """Validate team data and return list of errors"""
        errors = []

        try:
            # Check selected players count
            selected_count = (
                self.player_table.get_selected_count() if self.player_table else 0
            )
            if selected_count != 11:
                errors.append(
                    f"Must have exactly 11 players selected (current: {selected_count})"
                )

            # Check for duplicate player numbers
            player_numbers = []
            if self.player_table:
                for row in range(self.player_table.rowCount()):
                    num_item = self.player_table.item(row, 0)
                    if num_item and num_item.text().strip():
                        num = num_item.text().strip()
                        if num in player_numbers:
                            errors.append(f"Duplicate player number: {num}")
                        else:
                            player_numbers.append(num)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def get_panel_style(self, panel_type: str) -> str:
        """Get styling for different panel types"""
        base_style = """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
                margin: 5px;
            }
        """

        if panel_type == "left":
            return (
                base_style
                + """
                QFrame {
                    max-width: 780px;
                }
            """
            )
        elif panel_type == "right":
            return base_style
        elif panel_type == "control":
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f2937, stop:1 #111827);
                    border: 1px solid #4b5563;
                    border-radius: 6px;
                    margin: 2px;
                }
            """
        else:
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #374151, stop:1 #1f2937);
                    border: 1px solid #4b5563;
                    border-radius: 6px;
                    margin: 2px;
                }
            """

    def get_group_style(self) -> str:
        """Get styling for group frames"""
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
                margin: 1px;
            }
        """

    def get_label_style(self) -> str:
        """Get styling for labels"""
        return """
            QLabel {
                color: #e5e7eb;
                font-size: 12px;
                font-weight: 600;
                padding: 2px;
            }
        """

    def get_combobox_style(self) -> str:
        """Get styling for combo boxes"""
        return """
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
                color: #e5e7eb;
                font-size: 12px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: 1px solid #4b5563;
                width: 10px;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: url("resources/images/dropdown.png");
                width: 20px;
                height: 24px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }
            QComboBox QAbstractItemView {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                color: #e5e7eb;
                selection-background-color: #3b82f6;
            }
        """

    def get_image_label_style(self) -> str:
        """Get styling for image labels"""
        return """
            QLabel {
                background: #374151;
                border: 2px solid #4b5563;
                border-radius: 8px;
                color: #9ca3af;
                font-size: 10px;
                font-weight: 500;
            }
        """

    def get_button_style(self) -> str:
        """Get styling for buttons"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
                border: 1px solid #1e40af;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 #1e3a8a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1d4ed8, stop:1 #1e40af);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
                border-color: #065f46;
            }
        """

    def toggle_coordinate_display(self):
        """Toggle coordinate display for player markers"""
        try:
            show_coords = self.coord_toggle_button.isChecked()
            print(f"Toggling coordinate display: {show_coords} in {self.team_name}")

            # Update button text
            if show_coords:
                self.coord_toggle_button.setText("Hide Coordinates")
            else:
                self.coord_toggle_button.setText("Show Coordinates")

            # Update content panel
            if hasattr(self, "content_panel"):
                self.content_panel.set_coordinate_display(show_coords)

                # Emit data changed signal
                self.data_changed.emit()
        except Exception as e:
            print(f"Error toggling coordinate display: {e}")
            import traceback

            traceback.print_exc()

    def on_reload_formation_clicked(self):
        """Re-apply the current formation to the field display immediately."""
        try:
            # Use existing logic to apply the current formation
            formation_input = getattr(self.control_panel, "formation_input", None)
            formation = (
                formation_input.text().strip()
                if formation_input
                else "Select Formation"
            )
            if not formation:
                formation = "Select Formation"
            # Use the same player structure used elsewhere so IDs/numbers persist
            selected_players = self.get_selected_players()

            if (
                hasattr(self, "content_panel")
                and formation != "Select Formation"
                and len(selected_players) == 11
            ):
                self.content_panel.update_formation(formation)
                self.content_panel.update_selected_players(
                    selected_players, self.current_data_source
                )
                # Ensure team color is reapplied too
                color = (
                    self.team_a_color_1
                    if self.current_data_source == "Team A"
                    else self.team_b_color_1
                )
                self.content_panel.update_team_color(color)
            else:
                # If not valid, clear to reflect current state
                if hasattr(self, "content_panel"):
                    self.content_panel.clear_field()
        except Exception as e:
            print(f"Error reloading formation for {self.team_name}: {e}")

    def showEvent(self, event):
        """Handle when the team panel becomes visible"""
        super().showEvent(event)
        try:
            print(f"Team panel {self.team_name} became visible")
            # Apply the current formation when the tab becomes visible
            self.apply_current_formation()
        except Exception as e:
            print(f"Error in showEvent for {self.team_name}: {e}")

    def apply_current_formation(self):
        """Apply the current formation to the content panel"""
        try:
            if not hasattr(self, "content_panel"):
                return

            # Get the current team data
            team_data = (
                self.team_a_data
                if self.current_data_source == "Team A"
                else self.team_b_data
            )

            # Apply formation after a short delay to ensure player table is populated
            QTimer.singleShot(
                100,
                lambda: self._apply_formation_after_load(
                    self.current_data_source, team_data
                ),
            )

        except Exception as e:
            print(f"Error applying current formation for {self.team_name}: {e}")
            import traceback

            traceback.print_exc()

    def _apply_formation_after_load(self, data_source: str, team_data: Dict[str, Any]):
        """Apply formation after player table has been populated"""
        try:
            if not hasattr(self, "content_panel") or not team_data:
                return

            # Get the current formation
            current_formation = (
                self.team_a_formation
                if data_source == "Team A"
                else self.team_b_formation
            )

            # Get selected players from the player table
            selected_players = self.get_all_players_for_field()

            print(
                f"[{self.team_name}] Applying formation after load: {current_formation}, players: {len(selected_players)}"
            )

            # Apply formation only if we have exactly 11 players and a valid formation
            if current_formation != "Select Formation" and len(selected_players) == 11:
                # SIMPLIFIED: No need to manage state flags - ContentPanel handles this via global pool
                self.content_panel.update_formation(current_formation)
                self.content_panel.update_selected_players(
                    selected_players, data_source
                )
                # Apply stored per-team color to this panel only
                color = (
                    self.team_a_color_1
                    if data_source == "Team A"
                    else self.team_b_color_1
                )
                self.content_panel.update_team_color(color)
                # No need to force scaling since we now use consistent scene rectangles
            else:
                # Clear the field if no formation or not exactly 11 players
                self.content_panel.clear_players()

        except Exception:
            pass

    def get_all_players_for_field(self) -> list:
        """Get all selected players for the field display"""
        players_for_field = []
        try:
            for row in range(self.player_table.rowCount()):
                if not self.player_table.is_row_selected(row):
                    continue

                num_item = self.player_table.item(row, 0)
                name_item = self.player_table.item(row, 1)
                id_item = self.player_table.item(row, 2)
                pos_item = self.player_table.item(row, 3)

                jersey_no = num_item.text().strip() if num_item else ""
                full_name = name_item.text().strip() if name_item else ""
                player_id = id_item.text().strip() if id_item else ""
                position = pos_item.text().strip() if pos_item else ""

                player_data = {
                    "jersey_no": jersey_no,
                    "jersey_number": jersey_no,
                    "full_name": full_name,
                    "name": full_name,
                    "id": player_id,
                    "position": position,
                    "row": row,
                }
                players_for_field.append(player_data)

            print(
                f"[{self.team_name}] Got {len(players_for_field)} selected players from player table"
            )
        except Exception as e:
            print(f"[{self.team_name}] Error collecting players for field: {e}")

        return players_for_field

    def reset_team_data(self):
        """Reset the current team's formation and player selections"""
        try:
            # Get current data source (Team A or Team B)
            current_source = self.formation_panel.get_current_data_source()

            # Reset player selections for current team
            if current_source == "Team A":
                self.team_a_selected_rows.clear()
                self.team_a_selected_count = 0
                self.team_a_formation = "Select Formation"
                self.team_a_field_labels.clear()
            else:  # Team B
                self.team_b_selected_rows.clear()
                self.team_b_selected_count = 0
                self.team_b_formation = "Select Formation"
                self.team_b_field_labels.clear()

            # Clear player table selections
            self.player_table.clear_selections()

            # Reset formation combo box
            if hasattr(self.formation_panel, "formation_combo"):
                self.formation_panel.formation_combo.setCurrentText("Select Formation")

            # Clear only the active formation label
            if current_source == "Team A":
                if hasattr(self.formation_panel, "update_team_a_formation"):
                    self.formation_panel.update_team_a_formation(
                        "Select Formation", maintain_width=True
                    )
                    sibling_panel = self._find_sibling_panel()
                    if sibling_panel:
                        sibling_panel.team_a_formation = "Select Formation"
                        if hasattr(sibling_panel, "formation_panel"):
                            sibling_panel.formation_panel.update_team_a_formation(
                                "Select Formation", maintain_width=True
                            )
            else:
                if hasattr(self.formation_panel, "update_team_b_formation"):
                    self.formation_panel.update_team_b_formation(
                        "Select Formation", maintain_width=True
                    )
                    sibling_panel = self._find_sibling_panel()
                    if sibling_panel:
                        sibling_panel.team_b_formation = "Select Formation"
                        if hasattr(sibling_panel, "formation_panel"):
                            sibling_panel.formation_panel.update_team_b_formation(
                                "Select Formation", maintain_width=True
                            )

            # Clear field display and reset manual positioning flag
            if hasattr(self, "content_panel"):
                self.content_panel.clear_field()
                # Clear saved positions from global pools
                match_setup_tab = self.content_panel._get_match_setup_tab()
                if match_setup_tab:
                    # Clear both pools on reset
                    match_setup_tab.pool_a_positions.clear()
                    match_setup_tab.pool_b_positions.clear()
                    print(f"[{self.team_name}] Cleared global position pools on reset")

            # Update selected count display
            if hasattr(self, "info_panel"):
                self.info_panel.update_selected_count(0)

            # CRITICAL: Explicitly clear global pools when resetting
            # Find MatchSetupTab and directly clear the appropriate pool
            parent = self.parent()
            match_setup_tab = None
            while parent:
                if hasattr(parent, "a_selected_rows"):
                    match_setup_tab = parent
                    break
                parent = parent.parent()

            if match_setup_tab:
                # Explicitly clear the global pools for the current data source
                if current_source == "Team A":
                    match_setup_tab.a_selected_rows = set()
                    match_setup_tab.pool_a_formation = "Select Formation"
                    if hasattr(match_setup_tab, "pool_a_allow_fixture_defaults"):
                        match_setup_tab.pool_a_allow_fixture_defaults = False
                    print(f"[{self.team_name}] Cleared Team A pool in global state")
                else:
                    match_setup_tab.b_selected_rows = set()
                    match_setup_tab.pool_b_formation = "Select Formation"
                    if hasattr(match_setup_tab, "pool_b_allow_fixture_defaults"):
                        match_setup_tab.pool_b_allow_fixture_defaults = False
                    print(f"[{self.team_name}] Cleared Team B pool in global state")

            # Emit data changed signal
            self.data_changed.emit()

            print(f"[{self.team_name}] Team data reset completed successfully")

        except Exception as e:
            print(f"Error resetting team data for {self.team_name}: {e}")
            QMessageBox.warning(
                self, "Reset Error", f"Failed to reset team data: {str(e)}"
            )

    def _find_sibling_panel(self):
        """Locate the opposite team panel within MatchSetupTab."""
        try:
            match_setup_tab = self.parent()
            while match_setup_tab and not hasattr(match_setup_tab, "home_team_panel"):
                match_setup_tab = match_setup_tab.parent()
            if not match_setup_tab:
                return None
            if self is getattr(match_setup_tab, "home_team_panel", None):
                return getattr(match_setup_tab, "away_team_panel", None)
            if self is getattr(match_setup_tab, "away_team_panel", None):
                return getattr(match_setup_tab, "home_team_panel", None)
            return None
        except Exception:
            return None

    def _get_match_setup_tab(self):
        parent = self.parent()
        while parent and not hasattr(parent, "home_team_panel"):
            parent = parent.parent()
        return parent

    def _update_match_setup_team_data_formation(self, team_key: str, formation: str):
        match_setup_tab = self._get_match_setup_tab()
        if not match_setup_tab:
            return
        formation = formation or TeamConstants.SELECT_FORMATION
        if team_key == TeamConstants.TEAM_A:
            if not getattr(match_setup_tab, "home_team_data", None):
                match_setup_tab.home_team_data = {}
            match_setup_tab.home_team_data[DataKeys.FORMATION] = formation
            if hasattr(match_setup_tab, "pool_a_formation"):
                match_setup_tab.pool_a_formation = formation
            # Ensure both panels reflect the updated formation for Team A
            if hasattr(match_setup_tab, "home_team_panel"):
                match_setup_tab.home_team_panel.team_a_formation = formation
                match_setup_tab.home_team_panel.refresh_formation_labels()
            if hasattr(match_setup_tab, "away_team_panel"):
                match_setup_tab.away_team_panel.team_a_formation = formation
                match_setup_tab.away_team_panel.refresh_formation_labels()
        else:
            if not getattr(match_setup_tab, "away_team_data", None):
                match_setup_tab.away_team_data = {}
            match_setup_tab.away_team_data[DataKeys.FORMATION] = formation
            if hasattr(match_setup_tab, "pool_b_formation"):
                match_setup_tab.pool_b_formation = formation
            # Ensure both panels reflect the updated formation for Team B
            if hasattr(match_setup_tab, "home_team_panel"):
                match_setup_tab.home_team_panel.team_b_formation = formation
                match_setup_tab.home_team_panel.refresh_formation_labels()
            if hasattr(match_setup_tab, "away_team_panel"):
                match_setup_tab.away_team_panel.team_b_formation = formation
                match_setup_tab.away_team_panel.refresh_formation_labels()
