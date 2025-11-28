"""Match and Match Officials Data Models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
from .team import Team
from .match_config import MatchConfiguration


class MatchStatus(Enum):
    """Match status enumeration."""
    SETUP = "setup"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


@dataclass
class MatchOfficials:
    """
    Represents match officials assignment.
    
    Attributes:
        referee: Main referee name
        linesman_1: First linesman (optional)
        linesman_2: Second linesman (optional)
        fourth_official: Fourth official (optional)
        var_referee: VAR referee (optional)
        avar_referee: Assistant VAR referee (optional)
    """
    referee: str
    linesman_1: Optional[str] = None
    linesman_2: Optional[str] = None
    fourth_official: Optional[str] = None
    var_referee: Optional[str] = None
    avar_referee: Optional[str] = None

    def __post_init__(self):
        """Validate officials data after initialization."""
        if not self.referee or not self.referee.strip():
            raise ValueError("Main referee is required")

    def has_linesmen(self) -> bool:
        """Check if linesmen are assigned."""
        return bool(self.linesman_1 or self.linesman_2)

    def has_complete_officiating_team(self) -> bool:
        """Check if complete officiating team is assigned."""
        return bool(
            self.referee and
            self.linesman_1 and
            self.linesman_2 and
            self.fourth_official
        )

    def to_dict(self) -> dict:
        """Convert officials to dictionary for serialization."""
        return {
            "referee": self.referee,
            "linesman_1": self.linesman_1,
            "linesman_2": self.linesman_2,
            "fourth_official": self.fourth_official,
            "var_referee": self.var_referee,
            "avar_referee": self.avar_referee
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MatchOfficials':
        """Create officials from dictionary."""
        return cls(
            referee=data["referee"],
            linesman_1=data.get("linesman_1"),
            linesman_2=data.get("linesman_2"),
            fourth_official=data.get("fourth_official"),
            var_referee=data.get("var_referee"),
            avar_referee=data.get("avar_referee")
        )


@dataclass
class Match:
    """
    Represents a football match with all necessary information.
    
    Attributes:
        id: Unique identifier for the match (UUID format)
        tournament_id: ID of the tournament this match belongs to (optional)
        match_name: Descriptive name for the match
        match_number: Match number within tournament/season
        match_date: Date of the match
        match_time: Time of the match (as string, e.g., "15:30")
        venue: Match venue
        home_team: Home team
        away_team: Away team
        configuration: Match configuration and rules
        officials: Match officials assignment
        status: Current match status
        notes: Additional notes about the match (optional)
        created_date: When the match was created
    """
    id: str
    match_name: str
    match_number: int
    match_date: datetime
    match_time: str
    venue: str
    home_team: Team
    away_team: Team
    configuration: MatchConfiguration
    officials: MatchOfficials
    tournament_id: Optional[str] = None
    status: MatchStatus = MatchStatus.SETUP
    notes: Optional[str] = None
    created_date: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate match data after initialization."""
        if not self.id:
            raise ValueError("Match ID cannot be empty")
        if not self.match_name.strip():
            raise ValueError("Match name cannot be empty")
        if self.match_number < 1:
            raise ValueError("Match number must be positive")
        if not self.match_time.strip():
            raise ValueError("Match time cannot be empty")
        if not self.venue.strip():
            raise ValueError("Match venue cannot be empty")
        if self.home_team.id == self.away_team.id:
            raise ValueError("Home team and away team must be different")

    def get_match_title(self) -> str:
        """Get formatted match title."""
        return f"{self.home_team.short_name} vs {self.away_team.short_name}"

    def get_full_match_title(self) -> str:
        """Get full formatted match title."""
        return f"{self.home_team.full_name} vs {self.away_team.full_name}"

    def is_ready_to_start(self) -> bool:
        """Check if match is ready to start."""
        return (
            self.status == MatchStatus.SCHEDULED and
            self.home_team.has_goalkeeper() and
            self.away_team.has_goalkeeper() and
            not self.home_team.has_duplicate_jersey_numbers() and
            not self.away_team.has_duplicate_jersey_numbers() and
            self.officials.referee
        )

    def get_teams(self) -> tuple[Team, Team]:
        """Get both teams as tuple (home, away)."""
        return self.home_team, self.away_team

    def involves_team(self, team_id: str) -> bool:
        """Check if match involves a specific team."""
        return self.home_team.id == team_id or self.away_team.id == team_id

    def to_dict(self) -> dict:
        """Convert match to dictionary for serialization."""
        return {
            "id": self.id,
            "tournament_id": self.tournament_id,
            "match_name": self.match_name,
            "match_number": self.match_number,
            "match_date": self.match_date.isoformat(),
            "match_time": self.match_time,
            "venue": self.venue,
            "home_team": self.home_team.to_dict(),
            "away_team": self.away_team.to_dict(),
            "configuration": self.configuration.to_dict(),
            "officials": self.officials.to_dict(),
            "status": self.status.value,
            "notes": self.notes,
            "created_date": self.created_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Match':
        """Create match from dictionary."""
        return cls(
            id=data["id"],
            tournament_id=data.get("tournament_id"),
            match_name=data["match_name"],
            match_number=data["match_number"],
            match_date=datetime.fromisoformat(data["match_date"]),
            match_time=data["match_time"],
            venue=data["venue"],
            home_team=Team.from_dict(data["home_team"]),
            away_team=Team.from_dict(data["away_team"]),
            configuration=MatchConfiguration.from_dict(data["configuration"]),
            officials=MatchOfficials.from_dict(data["officials"]),
            status=MatchStatus(data.get("status", "setup")),
            notes=data.get("notes"),
            created_date=datetime.fromisoformat(data.get("created_date", datetime.utcnow().isoformat()))
        )
