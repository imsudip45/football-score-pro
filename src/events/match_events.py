"""Match Events Implementation"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..models.team import Team
from ..models.match import Match, MatchOfficials
from ..models.match_config import MatchConfiguration
from ..models.tournament import Tournament
from ..models.results import ValidationResult


@dataclass
class BaseEvent:
    """
    Base class for all events.
    
    Attributes:
        timestamp: When the event occurred
        event_id: Unique identifier for this event instance
        source: Source component that generated the event
    """
    # These will be set in __post_init__ to avoid dataclass ordering issues
    timestamp: datetime = field(init=False)
    event_id: Optional[str] = field(default=None, init=False)
    source: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize base event fields."""
        self.timestamp = datetime.utcnow()
        # event_id and source can be set by subclasses if needed

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "source": self.source
        }


@dataclass
class TeamImportedEvent(BaseEvent):
    """
    Event published when a team is successfully imported.
    
    Attributes:
        team_id: ID of the imported team
        team_data: Complete team object with all players
        players_count: Number of players imported
        file_path: Path to the imported file
        warnings: Any warnings generated during import
    """
    team_id: str
    team_data: Team
    players_count: int
    file_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "team_id": self.team_id,
            "team_data": self.team_data.to_dict(),
            "players_count": self.players_count,
            "file_path": self.file_path,
            "warnings": self.warnings
        })
        return base_dict

    def has_warnings(self) -> bool:
        """Check if import had warnings."""
        return len(self.warnings) > 0

    def get_team_summary(self) -> Dict[str, Any]:
        """Get team summary for UI display."""
        return {
            "id": self.team_id,
            "name": self.team_data.full_name,
            "short_name": self.team_data.short_name,
            "players_count": self.players_count,
            "manager": self.team_data.manager,
            "head_coach": self.team_data.head_coach,
            "has_goalkeeper": self.team_data.has_goalkeeper(),
            "has_duplicate_jerseys": self.team_data.has_duplicate_jersey_numbers()
        }


@dataclass
class MatchConfigurationUpdatedEvent(BaseEvent):
    """
    Event published when match configuration is updated.
    
    Attributes:
        match_id: ID of the match (if associated with a specific match)
        configuration: New match configuration
        changes: Dictionary of changed fields
        is_fifa_compliant: Whether new configuration is FIFA compliant
    """
    match_id: Optional[str]
    configuration: MatchConfiguration
    changes: Dict[str, Any]
    is_fifa_compliant: bool = field(init=False)
    
    def __post_init__(self):
        super().__post_init__()
        self.is_fifa_compliant = self.configuration.is_fifa_compliant()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "match_id": self.match_id,
            "configuration": self.configuration.to_dict(),
            "changes": self.changes,
            "is_fifa_compliant": self.is_fifa_compliant
        })
        return base_dict

    def has_significant_changes(self) -> bool:
        """Check if changes affect match gameplay."""
        significant_fields = [
            'first_half_duration', 'second_half_duration', 
            'max_substitutions', 'draw_allowed', 'extra_time_required'
        ]
        return any(field in self.changes for field in significant_fields)


@dataclass  
class MatchCreatedEvent(BaseEvent):
    """
    Event published when a match is successfully created.
    
    Attributes:
        match_id: ID of the created match
        match_data: Complete match object
        home_team_summary: Summary of home team
        away_team_summary: Summary of away team
        tournament_id: ID of associated tournament (if any)
        is_ready_to_start: Whether match is ready to start
    """
    match_id: str
    match_data: Match
    home_team_summary: Dict[str, Any]
    away_team_summary: Dict[str, Any]
    tournament_id: Optional[str] = None
    is_ready_to_start: bool = field(init=False)
    
    def __post_init__(self):
        super().__post_init__()
        self.tournament_id = self.match_data.tournament_id
        self.is_ready_to_start = self.match_data.is_ready_to_start()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "match_id": self.match_id,
            "match_data": self.match_data.to_dict(),
            "home_team_summary": self.home_team_summary,
            "away_team_summary": self.away_team_summary,
            "tournament_id": self.tournament_id,
            "is_ready_to_start": self.is_ready_to_start
        })
        return base_dict

    def get_match_title(self) -> str:
        """Get formatted match title."""
        return self.match_data.get_match_title()

    def get_teams_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about both teams."""
        return {
            "home": self.home_team_summary,
            "away": self.away_team_summary
        }


@dataclass
class OfficialsAssignedEvent(BaseEvent):
    """
    Event published when officials are assigned to a match.
    
    Attributes:
        match_id: ID of the match
        officials: Assigned officials
        is_complete_team: Whether complete officiating team is assigned
        previous_officials: Previous officials assignment (if any)
    """
    match_id: str
    officials: MatchOfficials
    is_complete_team: bool = field(init=False)
    previous_officials: Optional[MatchOfficials] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.is_complete_team = self.officials.has_complete_officiating_team()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "match_id": self.match_id,
            "officials": self.officials.to_dict(),
            "is_complete_team": self.is_complete_team,
            "previous_officials": self.previous_officials.to_dict() if self.previous_officials else None
        })
        return base_dict

    def get_officials_summary(self) -> Dict[str, Any]:
        """Get officials summary for UI display."""
        return {
            "referee": self.officials.referee,
            "assistant_referees": [
                self.officials.linesman_1,
                self.officials.linesman_2
            ],
            "fourth_official": self.officials.fourth_official,
            "var_team": {
                "var_referee": self.officials.var_referee,
                "assistant_var": self.officials.avar_referee
            },
            "is_complete": self.is_complete_team,
            "has_var": bool(self.officials.var_referee)
        }


@dataclass
class TournamentCreatedEvent(BaseEvent):
    """
    Event published when a tournament is created.
    
    Attributes:
        tournament_id: ID of the created tournament
        tournament_data: Complete tournament object
        configuration_preset: Configuration preset used (if any)
    """
    tournament_id: str
    tournament_data: Tournament
    configuration_preset: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "tournament_id": self.tournament_id,
            "tournament_data": self.tournament_data.to_dict(),
            "configuration_preset": self.configuration_preset
        })
        return base_dict

    def get_tournament_summary(self) -> Dict[str, Any]:
        """Get tournament summary for UI display."""
        return {
            "id": self.tournament_id,
            "name": self.tournament_data.name,
            "season": self.tournament_data.season,
            "status": self.tournament_data.get_status(),
            "duration_days": self.tournament_data.get_duration_days(),
            "match_type": self.tournament_data.rules.match_type,
            "is_fifa_compliant": self.tournament_data.rules.is_fifa_compliant()
        }


@dataclass
class TournamentDeletedEvent(BaseEvent):
    """
    Event published when a tournament is deleted.
    
    Attributes:
        tournament_id: ID of the deleted tournament
        tournament_name: Name of the deleted tournament
    """
    tournament_id: str
    tournament_name: str
    
    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name
        })
        return base_dict


@dataclass
class MatchDeletedEvent(BaseEvent):
    """
    Event published when a match is deleted.
    
    Attributes:
        match_id: ID of the deleted match
        match_name: Name of the deleted match
    """
    match_id: str
    match_name: str
    
    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "match_id": self.match_id,
            "match_name": self.match_name
        })
        return base_dict


# Helper functions for creating events
def create_team_imported_event(team_id: str, team: Team, players_count: int, file_path: Optional[str] = None, warnings: Optional[List[str]] = None) -> TeamImportedEvent:
    """Create a TeamImportedEvent with proper defaults."""
    return TeamImportedEvent(
        team_id=team_id,
        team_data=team,
        players_count=players_count,
        file_path=file_path,
        warnings=warnings or []
    )


def create_match_created_event(match: Match) -> MatchCreatedEvent:
    """Create a MatchCreatedEvent with team summaries."""
    home_summary = {
        "id": match.home_team.id,
        "name": match.home_team.full_name,
        "short_name": match.home_team.short_name,
        "player_count": len(match.home_team.get_all_players())
    }
    
    away_summary = {
        "id": match.away_team.id,
        "name": match.away_team.full_name,
        "short_name": match.away_team.short_name,
        "player_count": len(match.away_team.get_all_players())
    }
    
    return MatchCreatedEvent(
        match_id=match.id,
        match_data=match,
        home_team_summary=home_summary,
        away_team_summary=away_summary
    )


def create_officials_assigned_event(match_id: str, officials: MatchOfficials, previous_officials: Optional[MatchOfficials] = None) -> OfficialsAssignedEvent:
    """Create an OfficialsAssignedEvent with proper defaults."""
    return OfficialsAssignedEvent(
        match_id=match_id,
        officials=officials,
        previous_officials=previous_officials
    )


@dataclass
class SideAssignmentChangedEvent(BaseEvent):
    """
    Event published when side assignments change (home/away team selection).

    Attributes:
        home_uses_a: Whether home team uses side A
        effective_home_team: ID of the effective home team
        effective_away_team: ID of the effective away team
    """
    home_uses_a: bool
    effective_home_team: Optional[str] = None
    effective_away_team: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "home_uses_a": self.home_uses_a,
            "effective_home_team": self.effective_home_team,
            "effective_away_team": self.effective_away_team
        })
        return base_dict

    def get_assignment_summary(self) -> Dict[str, Any]:
        """Get assignment summary for UI display."""
        return {
            "home_uses_a": self.home_uses_a,
            "home_team": self.effective_home_team,
            "away_team": self.effective_away_team,
            "assignment_changed": True
        }


@dataclass
class TeamSelectionChangedEvent(BaseEvent):
    """
    Event published when team player selection changes.

    Attributes:
        team_id: ID of the team
        side: Side ("A" or "B")
        selected_player_ids: Set of selected player IDs
        selection_count: Number of selected players
        can_select_more: Whether more players can be selected
    """
    team_id: str
    side: str
    selected_player_ids: set
    selection_count: int
    can_select_more: bool

    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "team_id": self.team_id,
            "side": self.side,
            "selected_player_ids": list(self.selected_player_ids),
            "selection_count": self.selection_count,
            "can_select_more": self.can_select_more
        })
        return base_dict

    def get_selection_summary(self) -> Dict[str, Any]:
        """Get selection summary for UI display."""
        return {
            "team_id": self.team_id,
            "side": self.side,
            "selected_count": self.selection_count,
            "max_players": 11,
            "can_select_more": self.can_select_more,
            "selected_player_ids": list(self.selected_player_ids)
        }


@dataclass
class FormationPositionChangedEvent(BaseEvent):
    """
    Event published when a formation position changes.

    Attributes:
        team_id: ID of the team
        side: Side ("A" or "B")
        player_name: Name of the player
        x: X coordinate
        y: Y coordinate
        position_changed: Whether position was changed (vs cleared)
        position_cleared: Whether position was cleared
    """
    team_id: str
    side: str
    player_name: str
    x: int
    y: int
    position_changed: bool = True
    position_cleared: bool = False

    def __post_init__(self):
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "team_id": self.team_id,
            "side": self.side,
            "player_name": self.player_name,
            "x": self.x,
            "y": self.y,
            "position_changed": self.position_changed,
            "position_cleared": self.position_cleared
        })
        return base_dict

    def get_position_summary(self) -> Dict[str, Any]:
        """Get position summary for UI display."""
        return {
            "team_id": self.team_id,
            "side": self.side,
            "player_name": self.player_name,
            "position": (self.x, self.y) if self.position_changed else None,
            "position_changed": self.position_changed,
            "position_cleared": self.position_cleared
        }