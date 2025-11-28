"""Player Data Model"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    """
    Represents a football player with all necessary information.
    
    Attributes:
        id: Unique identifier for the player (UUID format)
        team_id: ID of the team this player belongs to
        full_name: Complete name of the player
        short_name: Shortened name for display purposes
        jersey_number: Player's jersey number (1-99)
        position: Standardized position ("GK", "DEF", "MID", "FWD")
        nationality: Player's nationality (optional)
        photo_url: URL to player's photo (optional)
        video_url: URL to player's video content (optional)
    """
    id: str
    team_id: str
    full_name: str
    short_name: str
    jersey_number: int
    position: str  # Standardized: "GK", "DEF", "MID", "FWD"
    nationality: Optional[str] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None

    def __post_init__(self):
        """Validate player data after initialization."""
        if not self.id:
            raise ValueError("Player ID cannot be empty")
        if not self.team_id:
            raise ValueError("Team ID cannot be empty")
        if not self.full_name.strip():
            raise ValueError("Player full name cannot be empty")
        if not self.short_name.strip():
            raise ValueError("Player short name cannot be empty")
        if not isinstance(self.jersey_number, int) or self.jersey_number < 1 or self.jersey_number > 99:
            raise ValueError("Jersey number must be an integer between 1 and 99")
        if self.position not in ["GK", "DEF", "MID", "FWD"]:
            raise ValueError("Position must be one of: GK, DEF, MID, FWD")

    def is_goalkeeper(self) -> bool:
        """Check if this player is a goalkeeper."""
        return self.position == "GK"

    def to_dict(self) -> dict:
        """Convert player to dictionary for serialization."""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "full_name": self.full_name,
            "short_name": self.short_name,
            "jersey_number": self.jersey_number,
            "position": self.position,
            "nationality": self.nationality,
            "photo_url": self.photo_url,
            "video_url": self.video_url
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        """Create player from dictionary."""
        return cls(
            id=data["id"],
            team_id=data["team_id"],
            full_name=data["full_name"],
            short_name=data["short_name"],
            jersey_number=data["jersey_number"],
            position=data["position"],
            nationality=data.get("nationality"),
            photo_url=data.get("photo_url"),
            video_url=data.get("video_url")
        )
