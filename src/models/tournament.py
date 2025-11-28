"""Tournament Data Model"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .match_config import MatchConfiguration


@dataclass
class Tournament:
    """
    Represents a football tournament with all necessary information.
    
    Attributes:
        id: Unique identifier for the tournament (UUID format)
        name: Tournament name
        season: Season identifier (e.g., "2024-25")
        start_date: Tournament start date
        end_date: Tournament end date
        rules: Default match configuration for this tournament
        description: Tournament description (optional)
        organizer: Tournament organizer (optional)
        venue: Main venue or venues (optional)
        created_date: When the tournament was created
    """
    id: str
    name: str
    season: str
    start_date: datetime
    end_date: datetime
    rules: MatchConfiguration
    description: Optional[str] = None
    organizer: Optional[str] = None
    venue: Optional[str] = None
    created_date: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate tournament data after initialization."""
        if not self.id:
            raise ValueError("Tournament ID cannot be empty")
        if not self.name.strip():
            raise ValueError("Tournament name cannot be empty")
        if not self.season.strip():
            raise ValueError("Tournament season cannot be empty")
        if self.start_date >= self.end_date:
            raise ValueError("Tournament start date must be before end date")

    def is_active(self) -> bool:
        """Check if tournament is currently active."""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date

    def is_upcoming(self) -> bool:
        """Check if tournament is upcoming."""
        return datetime.utcnow() < self.start_date

    def is_finished(self) -> bool:
        """Check if tournament is finished."""
        return datetime.utcnow() > self.end_date

    def get_duration_days(self) -> int:
        """Get tournament duration in days."""
        return (self.end_date - self.start_date).days

    def get_status(self) -> str:
        """Get tournament status as string."""
        if self.is_upcoming():
            return "Upcoming"
        elif self.is_active():
            return "Active"
        else:
            return "Finished"

    def to_dict(self) -> dict:
        """Convert tournament to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "season": self.season,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "rules": self.rules.to_dict(),
            "description": self.description,
            "organizer": self.organizer,
            "venue": self.venue,
            "created_date": self.created_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Tournament':
        """Create tournament from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            season=data["season"],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
            rules=MatchConfiguration.from_dict(data["rules"]),
            description=data.get("description"),
            organizer=data.get("organizer"),
            venue=data.get("venue"),
            created_date=datetime.fromisoformat(data.get("created_date", datetime.utcnow().isoformat()))
        )
