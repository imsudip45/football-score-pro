"""
Backend Service Wrapper for PySide6 UI Integration
Bridges backend events to Qt signals for seamless UI updates
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.events.match_events import (
    FormationPositionChangedEvent,
    MatchConfigurationUpdatedEvent,
    MatchCreatedEvent,
    OfficialsAssignedEvent,
    SideAssignmentChangedEvent,
    TeamImportedEvent,
    TeamSelectionChangedEvent,
)
from src.events.officials_events import OfficialsPoolLoadedEvent
from src.models.match import Match
from src.models.official import Official, OfficialsPool, OfficialType
from src.models.results import CreateResult, ImportResult, SaveResult, ValidationResult
from src.models.team import Team
from src.models.tournament import Tournament
from src.services.interfaces import (
    IEventBus,
    IFixtureService,
    IFormationLayoutService,
    IMatchService,
    IOfficialsService,
    ISideAssignmentService,
    ITeamSelectionService,
    ITeamService,
    ITournamentService,
    IValidationService,
)


class BackendService(QObject):
    """
    Backend Service Wrapper that bridges backend events to Qt signals
    Provides a clean interface for UI components to interact with backend services
    """

    # Qt Signals for UI updates
    team_imported = Signal(object)  # TeamImportedEvent
    match_created = Signal(object)  # MatchCreatedEvent
    officials_assigned = Signal(object)  # OfficialsAssignedEvent
    match_configuration_updated = Signal(object)  # MatchConfigurationUpdatedEvent
    officials_pool_loaded = Signal(object)  # OfficialsPoolLoadedEvent
    side_assignment_changed = Signal(object)  # SideAssignmentChangedEvent
    team_selection_changed = Signal(object)  # TeamSelectionChangedEvent
    formation_position_changed = Signal(object)  # FormationPositionChangedEvent

    # Data change signals
    teams_updated = Signal()
    matches_updated = Signal()
    tournaments_updated = Signal()
    officials_updated = Signal()

    # Error signals
    error_occurred = Signal(str, str)  # error_type, error_message

    def __init__(
        self,
        team_service: ITeamService,
        match_service: IMatchService,
        tournament_service: ITournamentService,
        validation_service: IValidationService,
        event_bus: IEventBus,
        officials_service: IOfficialsService,
        fixture_service: IFixtureService,
        side_assignment_service: ISideAssignmentService,
        team_selection_service: ITeamSelectionService,
        formation_layout_service: IFormationLayoutService,
        parent=None,
    ):
        super().__init__(parent)

        self.team_service = team_service
        self.match_service = match_service
        self.tournament_service = tournament_service
        self.validation_service = validation_service
        self.event_bus = event_bus
        self.officials_service = officials_service
        self.fixture_service = fixture_service
        self.side_assignment_service = side_assignment_service
        self.team_selection_service = team_selection_service
        self.formation_layout_service = formation_layout_service

        # Setup event subscriptions
        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self):
        """Setup event subscriptions to bridge backend events to Qt signals"""

        def on_team_imported(event: TeamImportedEvent):
            self.team_imported.emit(event)
            self.teams_updated.emit()

        def on_match_created(event: MatchCreatedEvent):
            self.match_created.emit(event)
            self.matches_updated.emit()

        def on_officials_assigned(event: OfficialsAssignedEvent):
            self.officials_assigned.emit(event)
            self.matches_updated.emit()

        def on_match_configuration_updated(event: MatchConfigurationUpdatedEvent):
            self.match_configuration_updated.emit(event)
            self.matches_updated.emit()

        def on_officials_pool_loaded(event: OfficialsPoolLoadedEvent):
            self.officials_pool_loaded.emit(event)
            self.officials_updated.emit()

        def on_side_assignment_changed(event: SideAssignmentChangedEvent):
            self.side_assignment_changed.emit(event)

        def on_team_selection_changed(event: TeamSelectionChangedEvent):
            self.team_selection_changed.emit(event)

        def on_formation_position_changed(event: FormationPositionChangedEvent):
            self.formation_position_changed.emit(event)

        # Subscribe to events
        self.event_bus.subscribe("team_imported", on_team_imported)
        self.event_bus.subscribe("match_created", on_match_created)
        self.event_bus.subscribe("officials_assigned", on_officials_assigned)
        self.event_bus.subscribe(
            "match_configuration_updated", on_match_configuration_updated
        )
        self.event_bus.subscribe("officials_pool_loaded", on_officials_pool_loaded)
        self.event_bus.subscribe("side_assignment_changed", on_side_assignment_changed)
        self.event_bus.subscribe("team_selection_changed", on_team_selection_changed)
        self.event_bus.subscribe(
            "formation_position_changed", on_formation_position_changed
        )

    # Team Service Methods
    def import_team_from_json(self, file_path: str) -> ImportResult:
        """Import team from JSON file"""
        try:
            import json
            from pathlib import Path

            # Read the JSON file
            path = Path(file_path)
            if not path.exists():
                return ImportResult(
                    success=False, errors=[f"File not found: {file_path}"]
                )

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            # Check if it's a teams array structure
            if "teams" in data and isinstance(data["teams"], list):
                # Import all teams from the array
                imported_teams = []
                all_errors = []
                all_warnings = []

                for team_data in data["teams"]:
                    result = self.team_service.import_from_json_data(team_data)
                    if result.success:
                        imported_teams.append(result.team)
                        all_warnings.extend(result.warnings)
                    else:
                        all_errors.extend(result.errors)

                if imported_teams:
                    # Return success with the first imported team
                    return ImportResult(
                        success=True,
                        team=imported_teams[0],
                        errors=all_errors,
                        warnings=all_warnings,
                        file_path=file_path,
                    )
                else:
                    return ImportResult(
                        success=False,
                        errors=all_errors,
                        warnings=all_warnings,
                        file_path=file_path,
                    )
            else:
                # Single team structure
                result = self.team_service.import_from_json_data(data)
                if not result.success:
                    self.error_occurred.emit(
                        "team_import",
                        f"Failed to import team: {', '.join(result.errors)}",
                    )
                return result

        except Exception as e:
            self.error_occurred.emit(
                "team_import", f"Unexpected error importing team: {str(e)}"
            )
            return ImportResult(success=False, errors=[str(e)], file_path=file_path)

    def import_team_from_data(self, team_data: Dict[str, Any]) -> ImportResult:
        """Import team from data dictionary"""
        try:
            result = self.team_service.import_from_json_data(team_data)
            if not result.success:
                self.error_occurred.emit(
                    "team_import", f"Failed to import team: {', '.join(result.errors)}"
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "team_import", f"Unexpected error importing team: {str(e)}"
            )
            return ImportResult(success=False, errors=[str(e)])

    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        return self.team_service.get_team_by_id(team_id)

    def get_all_teams(self) -> list:
        """Get all teams"""
        return self.team_service.get_all_teams()

    def validate_team_composition(self, team_id: str) -> ValidationResult:
        """Validate team composition"""
        return self.team_service.validate_team_composition(team_id)

    # Match Service Methods
    def create_match(self, match_data: Dict[str, Any]) -> CreateResult:
        """Create a new match"""
        try:
            result = self.match_service.create_match(match_data)
            if not result.success:
                self.error_occurred.emit(
                    "match_creation",
                    f"Failed to create match: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "match_creation", f"Unexpected error creating match: {str(e)}"
            )
            return CreateResult.failure_result([str(e)])

    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get match by ID"""
        return self.match_service.get_match_by_id(match_id)

    def get_all_matches(self) -> list:
        """Get all matches"""
        return self.match_service.get_all_matches()

    def assign_officials(self, match_id: str, officials: Dict[str, str]) -> SaveResult:
        """Assign officials to match"""
        try:
            result = self.match_service.assign_officials(match_id, officials)
            if not result.success:
                self.error_occurred.emit(
                    "officials_assignment",
                    f"Failed to assign officials: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "officials_assignment",
                f"Unexpected error assigning officials: {str(e)}",
            )
            return SaveResult.failure_result([str(e)])

    def update_match_configuration(
        self, match_id: str, config_updates: Dict[str, Any]
    ) -> SaveResult:
        """Update match configuration"""
        try:
            result = self.match_service.update_configuration(match_id, config_updates)
            if not result.success:
                self.error_occurred.emit(
                    "config_update",
                    f"Failed to update configuration: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "config_update", f"Unexpected error updating configuration: {str(e)}"
            )
            return SaveResult.failure_result([str(e)])

    def validate_complete_match_setup(self, match_id: str) -> ValidationResult:
        """Validate complete match setup"""
        return self.match_service.validate_complete_setup(match_id)

    def save_match(self, match_id: str, file_path: str) -> SaveResult:
        """Save match to file"""
        try:
            result = self.match_service.save_match(match_id, file_path)
            if not result.success:
                self.error_occurred.emit(
                    "match_save", f"Failed to save match: {', '.join(result.errors)}"
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "match_save", f"Unexpected error saving match: {str(e)}"
            )
            return SaveResult.failure_result([str(e)])

    def load_match(self, file_path: str) -> ImportResult:
        """Load match from file"""
        try:
            result = self.match_service.load_match(file_path)
            if not result.success:
                self.error_occurred.emit(
                    "match_load", f"Failed to load match: {', '.join(result.errors)}"
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "match_load", f"Unexpected error loading match: {str(e)}"
            )
            return ImportResult(success=False, errors=[str(e)], file_path=file_path)

    def get_saved_matches(self, directory: str) -> list:
        """Get list of saved matches"""
        return self.match_service.get_saved_matches(directory)

    def delete_match(self, match_id: str) -> SaveResult:
        """Delete match"""
        try:
            result = self.match_service.delete_match(match_id)
            if not result.success:
                self.error_occurred.emit(
                    "match_delete",
                    f"Failed to delete match: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "match_delete", f"Unexpected error deleting match: {str(e)}"
            )
            return SaveResult.failure_result([str(e)])

    # Runtime State Methods
    def save_runtime_state(
        self, match_id: str, runtime_state: Dict[str, Any]
    ) -> SaveResult:
        """Save runtime state under 'runtime' in match JSON."""
        try:
            result = self.match_service.update_runtime_state(match_id, runtime_state)
            if not result.success:
                self.error_occurred.emit(
                    "runtime_save",
                    f"Failed to save runtime state: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "runtime_save", f"Unexpected error saving runtime state: {str(e)}"
            )
            return SaveResult.failure_result([str(e)])

    def load_runtime_state(self, match_id: str) -> Dict[str, Any]:
        """Load runtime state from match JSON."""
        try:
            return self.match_service.get_runtime_state(match_id)
        except Exception as e:
            self.error_occurred.emit(
                "runtime_load", f"Unexpected error loading runtime state: {str(e)}"
            )
            return {}

    # Tournament Service Methods
    def get_tournaments(self) -> list:
        """Get all tournaments"""
        return self.tournament_service.get_tournaments()

    def create_tournament(self, tournament_data: Dict[str, Any]) -> CreateResult:
        """Create a new tournament"""
        try:
            result = self.tournament_service.create_tournament(tournament_data)
            if not result.success:
                self.error_occurred.emit(
                    "tournament_creation",
                    f"Failed to create tournament: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "tournament_creation", f"Unexpected error creating tournament: {str(e)}"
            )
            return CreateResult.failure_result([str(e)])

    def get_tournament_by_id(self, tournament_id: str) -> Optional[Tournament]:
        """Get tournament by ID"""
        return self.tournament_service.get_tournament_by_id(tournament_id)

    def get_configuration_presets(self) -> Dict[str, Any]:
        """Get configuration presets"""
        return self.tournament_service.get_configuration_presets()

    # Validation Service Methods
    def validate_team_composition_direct(self, team: Team) -> ValidationResult:
        """Validate team composition directly"""
        return self.validation_service.validate_team_composition(team)

    def validate_match_configuration_direct(self, config: Any) -> ValidationResult:
        """Validate match configuration directly"""
        return self.validation_service.validate_match_configuration(config)

    def validate_officials_assignment_direct(
        self, officials: Dict[str, str]
    ) -> ValidationResult:
        """Validate officials assignment directly"""
        return self.validation_service.validate_officials_assignment(officials)

    def validate_tournament_rules_direct(
        self, tournament: Tournament
    ) -> ValidationResult:
        """Validate tournament rules directly"""
        return self.validation_service.validate_tournament_rules(tournament)

    # Officials Service Methods
    def load_officials_pool(
        self, pool_data: Dict[str, Any], tournament_id: Optional[str] = None
    ) -> CreateResult:
        """Load officials pool from data"""
        try:
            result = self.officials_service.load_officials_pool(
                pool_data, tournament_id
            )
            if not result.success:
                self.error_occurred.emit(
                    "officials_load",
                    f"Failed to load officials pool: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "officials_load", f"Unexpected error loading officials pool: {str(e)}"
            )
            return CreateResult.failure_result([str(e)])

    def get_officials_pool(
        self, tournament_id: Optional[str] = None
    ) -> Optional[OfficialsPool]:
        """Get loaded officials pool"""
        return self.officials_service.get_officials_pool(tournament_id)

    def get_available_officials(
        self, official_type: OfficialType, tournament_id: Optional[str] = None
    ) -> List[Official]:
        """Get available officials by type"""
        return self.officials_service.get_available_officials(
            official_type, tournament_id
        )

    def normalize_officials_data(
        self, raw_data: Any, official_type: OfficialType
    ) -> List[Official]:
        """Normalize raw officials data"""
        return self.officials_service.normalize_officials_data(raw_data, official_type)

    def clear_officials_pool(self, tournament_id: Optional[str] = None) -> bool:
        """Clear officials pool"""
        return self.officials_service.clear_pool(tournament_id)

    # Fixture Service Methods
    def load_fixture_bundle(self, source: str) -> ImportResult:
        """Load fixture bundle from file or API"""
        try:
            result = self.fixture_service.load_fixture_bundle(source)
            if not result.success:
                self.error_occurred.emit(
                    "fixture_load",
                    f"Failed to load fixture: {', '.join(result.errors)}",
                )
            return result
        except Exception as e:
            self.error_occurred.emit(
                "fixture_load", f"Unexpected error loading fixture: {str(e)}"
            )
            return ImportResult(success=False, errors=[str(e)], file_path=source)

    def parse_fixture_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize fixture data"""
        return self.fixture_service.parse_fixture_data(raw_data)

    def extract_officials_pool_from_fixture(
        self, fixture_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract officials pool from fixture data"""
        return self.fixture_service.extract_officials_pool(fixture_data)

    def extract_teams_from_fixture(
        self, fixture_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract team data from fixture"""
        return self.fixture_service.extract_teams(fixture_data)

    def get_fixture_summary(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary information about a fixture"""
        return self.fixture_service.get_fixture_summary(fixture_data)

    # Side Assignment Service Methods
    def set_home_uses_a(self, uses_a: bool) -> None:
        """Set whether home team uses side A"""
        self.side_assignment_service.set_home_uses_a(uses_a)

    def get_home_uses_a(self) -> bool:
        """Get whether home team uses side A"""
        return self.side_assignment_service.get_home_uses_a()

    def get_effective_home_team(self) -> Optional[str]:
        """Get effective home team ID"""
        return self.side_assignment_service.get_effective_home_team()

    def get_effective_away_team(self) -> Optional[str]:
        """Get effective away team ID"""
        return self.side_assignment_service.get_effective_away_team()

    def get_side_for_team(self, team_id: str) -> Optional[str]:
        """Get which side a team is assigned to"""
        return self.side_assignment_service.get_side_for_team(team_id)

    def clear_side_assignments(self) -> None:
        """Clear all side assignments"""
        self.side_assignment_service.clear_assignment()

    # Team Selection Service Methods
    def set_selected_players(self, team_id: str, side: str, player_ids: set) -> None:
        """Set selected players for a team and side"""
        self.team_selection_service.set_selected_players(team_id, side, player_ids)

    def get_selected_players(self, team_id: str, side: str) -> set:
        """Get selected players for a team and side"""
        return self.team_selection_service.get_selected_players(team_id, side)

    def add_selected_player(self, team_id: str, side: str, player_id: str) -> bool:
        """Add a player to selection"""
        return self.team_selection_service.add_selected_player(team_id, side, player_id)

    def remove_selected_player(self, team_id: str, side: str, player_id: str) -> None:
        """Remove a player from selection"""
        self.team_selection_service.remove_selected_player(team_id, side, player_id)

    def can_select_more(self, team_id: str, side: str) -> bool:
        """Check if more players can be selected"""
        return self.team_selection_service.can_select_more(team_id, side)

    def get_selection_count(self, team_id: str, side: str) -> int:
        """Get selection count for team and side"""
        return self.team_selection_service.get_selection_count(team_id, side)

    def clear_team_selection(self, team_id: str, side: str) -> None:
        """Clear selection for a team and side"""
        self.team_selection_service.clear_selection(team_id, side)

    def clear_all_selections(self) -> None:
        """Clear all selections"""
        self.team_selection_service.clear_all_selections()

    # Formation Layout Service Methods
    def save_player_position(
        self, team_id: str, side: str, player_name: str, x: int, y: int
    ) -> None:
        """Save player position in formation"""
        self.formation_layout_service.save_player_position(
            team_id, side, player_name, x, y
        )

    def get_player_position(
        self, team_id: str, side: str, player_name: str
    ) -> Optional[tuple]:
        """Get saved player position"""
        return self.formation_layout_service.get_player_position(
            team_id, side, player_name
        )

    def get_all_positions(self, team_id: str, side: str) -> Dict[str, tuple]:
        """Get all saved positions for team and side"""
        return self.formation_layout_service.get_all_positions(team_id, side)

    def clear_team_positions(self, team_id: str, side: str) -> None:
        """Clear positions for a team and side"""
        self.formation_layout_service.clear_positions(team_id, side)

    def clear_all_positions(self) -> None:
        """Clear all positions"""
        self.formation_layout_service.clear_all_positions()

    def get_side_assignment_service(self) -> ISideAssignmentService:
        """Get side assignment service"""
        return self.side_assignment_service
