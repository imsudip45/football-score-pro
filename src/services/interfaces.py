"""Service interfaces for dependency injection and clear contracts."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.team import Team
from ..models.match import Match
from ..models.tournament import Tournament
from ..models.match_config import MatchConfiguration
from ..models.official import Official, OfficialsPool, OfficialType
from ..models.results import ImportResult, ValidationResult, SaveResult, CreateResult


class IValidationService(ABC):
    """Interface for validation service."""
    
    @abstractmethod
    def validate_team_composition(self, team: Team) -> ValidationResult:
        """Validate team composition including goalkeeper and player count."""
        pass
    
    @abstractmethod
    def validate_match_configuration(self, config: MatchConfiguration) -> ValidationResult:
        """Validate match configuration against FIFA rules."""
        pass
    
    @abstractmethod
    def validate_officials_assignment(self, officials: Dict[str, str]) -> ValidationResult:
        """Validate referee and assistant assignments."""
        pass
    
    @abstractmethod
    def validate_tournament_rules(self, tournament: Tournament) -> ValidationResult:
        """Validate tournament-specific rules and configuration."""
        pass


class ITeamService(ABC):
    """Interface for team service operations."""
    
    @abstractmethod
    def import_from_json(self, file_path: str) -> ImportResult:
        """Import team data from JSON file."""
        pass
    
    @abstractmethod
    def import_from_json_data(self, team_data: Dict[str, Any]) -> ImportResult:
        """Import team data from dictionary."""
        pass
    
    @abstractmethod
    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        pass
    
    @abstractmethod
    def get_all_teams(self) -> List[Team]:
        """Get all imported teams."""
        pass
    
    @abstractmethod
    def get_team_summary(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team summary for UI display."""
        pass
    
    @abstractmethod
    def validate_team_composition(self, team_id: str) -> ValidationResult:
        """Validate team composition by ID."""
        pass


class ITournamentService(ABC):
    """Interface for tournament service operations."""
    
    @abstractmethod
    def get_tournaments(self) -> List[Tournament]:
        """Get all tournaments."""
        pass
    
    @abstractmethod
    def create_tournament(self, tournament_data: Dict[str, Any]) -> CreateResult:
        """Create new tournament."""
        pass
    
    @abstractmethod
    def get_tournament_by_id(self, tournament_id: str) -> Optional[Tournament]:
        """Get tournament by ID."""
        pass
    
    @abstractmethod
    def get_tournament_rules(self, tournament_id: str) -> Optional[MatchConfiguration]:
        """Get tournament-specific match configuration."""
        pass
    
    @abstractmethod
    def get_configuration_presets(self) -> Dict[str, MatchConfiguration]:
        """Get predefined match configuration presets."""
        pass
    
    @abstractmethod
    def export_tournaments(self, file_path: str) -> bool:
        """Export tournaments to file."""
        pass


class IMatchService(ABC):
    """Interface for match service operations."""
    
    @abstractmethod
    def create_match(self, match_data: Dict[str, Any]) -> CreateResult:
        """Create new match."""
        pass
    
    @abstractmethod
    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get match by ID."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: MatchConfiguration) -> ValidationResult:
        """Validate match configuration."""
        pass
    
    @abstractmethod
    def validate_team_differences(self, home_team: Team, away_team: Team) -> ValidationResult:
        """Validate that teams are different and eligible."""
        pass
    
    @abstractmethod
    def validate_complete_setup(self, match_id: str) -> ValidationResult:
        """Validate complete match setup."""
        pass
    
    @abstractmethod
    def assign_officials(self, match_id: str, officials: Dict[str, str]) -> SaveResult:
        """Assign officials to match."""
        pass
    
    @abstractmethod
    def update_configuration(self, match_id: str, config_updates: Dict[str, Any]) -> SaveResult:
        """Update match configuration."""
        pass
    
    @abstractmethod
    def save_match(self, match_id: str, file_path: str) -> SaveResult:
        """Save match to file."""
        pass
    
    @abstractmethod
    def load_match(self, file_path: str) -> ImportResult:
        """Load match from file."""
        pass
    
    @abstractmethod
    def get_saved_matches(self, directory: str) -> List[Dict[str, Any]]:
        """Get list of saved matches with metadata."""
        pass
    
    @abstractmethod
    def delete_match(self, match_id: str) -> SaveResult:
        """Delete match and cleanup."""
        pass


class IEventBus(ABC):
    """Interface for event bus operations."""
    
    @abstractmethod
    def subscribe(self, event_type: str, handler) -> None:
        """Subscribe to event type."""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler) -> None:
        """Unsubscribe from event type."""
        pass
    
    @abstractmethod
    def publish(self, event_type: str, event) -> None:
        """Publish event."""
        pass
    
    @abstractmethod
    def clear_subscribers(self) -> None:
        """Clear all subscribers."""
        pass


class IOfficialsService(ABC):
    """Interface for officials service operations."""
    
    @abstractmethod
    def load_officials_pool(self, pool_data: Dict[str, Any], tournament_id: Optional[str] = None) -> CreateResult:
        """Load officials pool from data."""
        pass
    
    @abstractmethod
    def get_officials_pool(self, tournament_id: Optional[str] = None) -> Optional[OfficialsPool]:
        """Get loaded officials pool."""
        pass
    
    @abstractmethod
    def get_available_officials(self, official_type: OfficialType, tournament_id: Optional[str] = None) -> List[Official]:
        """Get available officials by type."""
        pass
    
    @abstractmethod
    def normalize_officials_data(self, raw_data: Any, official_type: OfficialType) -> List[Official]:
        """Normalize raw officials data (strings or dicts) into Official objects."""
        pass
    
    @abstractmethod
    def clear_pool(self, tournament_id: Optional[str] = None) -> bool:
        """Clear officials pool."""
        pass


class IFixtureService(ABC):
    """Interface for fixture service operations."""

    @abstractmethod
    def load_fixture_bundle(self, source: str) -> ImportResult:
        """Load fixture bundle from file or API URL."""
        pass

    @abstractmethod
    def parse_fixture_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize fixture data."""
        pass

    @abstractmethod
    def extract_officials_pool(self, fixture_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract officials pool from fixture data."""
        pass

    @abstractmethod
    def extract_teams(self, fixture_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract team data from fixture."""
        pass


class ISideAssignmentService(ABC):
    """Interface for side assignment service operations."""

    @abstractmethod
    def set_home_uses_a(self, uses_a: bool) -> None:
        """Set whether home team uses side A."""
        pass

    @abstractmethod
    def get_home_uses_a(self) -> bool:
        """Get whether home team uses side A."""
        pass

    @abstractmethod
    def get_effective_home_team(self) -> Optional[str]:
        """Get effective home team ID based on current assignment."""
        pass

    @abstractmethod
    def get_effective_away_team(self) -> Optional[str]:
        """Get effective away team ID based on current assignment."""
        pass

    @abstractmethod
    def get_side_for_team(self, team_id: str) -> Optional[str]:
        """Get which side (A or B) a team is assigned to."""
        pass

    @abstractmethod
    def clear_assignment(self) -> None:
        """Clear side assignments."""
        pass


class ITeamSelectionService(ABC):
    """Interface for team selection service operations."""

    @abstractmethod
    def set_selected_players(self, team_id: str, side: str, player_ids: set) -> None:
        """Set selected players for a team and side."""
        pass

    @abstractmethod
    def get_selected_players(self, team_id: str, side: str) -> set:
        """Get selected players for a team and side."""
        pass

    @abstractmethod
    def add_selected_player(self, team_id: str, side: str, player_id: str) -> bool:
        """Add a player to selection, returns True if successful (within limit)."""
        pass

    @abstractmethod
    def remove_selected_player(self, team_id: str, side: str, player_id: str) -> None:
        """Remove a player from selection."""
        pass

    @abstractmethod
    def can_select_more(self, team_id: str, side: str) -> bool:
        """Check if more players can be selected (within 11 limit)."""
        pass

    @abstractmethod
    def get_selection_count(self, team_id: str, side: str) -> int:
        """Get current selection count for team and side."""
        pass

    @abstractmethod
    def clear_selection(self, team_id: str, side: str) -> None:
        """Clear all selections for a team and side."""
        pass


class IFormationLayoutService(ABC):
    """Interface for formation layout service operations."""

    @abstractmethod
    def save_player_position(self, team_id: str, side: str, player_name: str, x: int, y: int) -> None:
        """Save player position in formation."""
        pass

    @abstractmethod
    def get_player_position(self, team_id: str, side: str, player_name: str) -> Optional[tuple]:
        """Get saved player position."""
        pass

    @abstractmethod
    def get_all_positions(self, team_id: str, side: str) -> Dict[str, tuple]:
        """Get all saved positions for team and side."""
        pass

    @abstractmethod
    def clear_positions(self, team_id: str, side: str) -> None:
        """Clear all positions for team and side."""
        pass

    @abstractmethod
    def clear_all_positions(self) -> None:
        """Clear all saved positions."""
        pass
