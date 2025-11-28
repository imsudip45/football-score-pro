"""Team Data Model"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .player import Player


@dataclass
class Team:
    """
    Represents a football team with all necessary information.
    
    Attributes:
        id: Unique identifier for the team (UUID format)
        full_name: Complete team name
        short_name: Abbreviated team name (3-4 characters)
        logo_url: URL to team logo (optional)
        manager: Team manager name (optional)
        head_coach: Head coach name (optional)
        assistant_coach: Assistant coach name (optional)
        total_players: Total number of players in the squad
        season: Season identifier (optional)
        created_date: When the team was created
        players: List of players in the main squad
        substitutes: List of substitute players
    """
    id: str
    full_name: str
    short_name: str
    logo_url: Optional[str] = None
    manager: Optional[str] = None
    head_coach: Optional[str] = None
    assistant_coach: Optional[str] = None
    total_players: int = 0
    season: Optional[str] = None
    created_date: datetime = field(default_factory=datetime.utcnow)
    players: List[Player] = field(default_factory=list)
    substitutes: List[Player] = field(default_factory=list)

    def __post_init__(self):
        """Validate team data after initialization."""
        if not self.id:
            raise ValueError("Team ID cannot be empty")
        if not self.full_name.strip():
            raise ValueError("Team full name cannot be empty")
        if not self.short_name.strip():
            raise ValueError("Team short name cannot be empty")
        if len(self.short_name) > 4:
            raise ValueError("Team short name cannot be longer than 4 characters")
        
        # Update total_players based on actual player count
        self.total_players = len(self.players) + len(self.substitutes)

    def get_all_players(self) -> List[Player]:
        """Get all players (main squad + substitutes)."""
        return self.players + self.substitutes

    def get_goalkeepers(self) -> List[Player]:
        """Get all goalkeepers in the team."""
        return [player for player in self.get_all_players() if player.is_goalkeeper()]

    def get_players_by_position(self, position: str) -> List[Player]:
        """Get all players in a specific position."""
        return [player for player in self.get_all_players() if player.position == position]

    def has_goalkeeper(self) -> bool:
        """Check if team has at least one goalkeeper."""
        return len(self.get_goalkeepers()) > 0

    def get_jersey_numbers(self) -> List[int]:
        """Get all jersey numbers used by the team."""
        return [player.jersey_number for player in self.get_all_players()]

    def has_duplicate_jersey_numbers(self) -> bool:
        """Check if team has duplicate jersey numbers."""
        jersey_numbers = self.get_jersey_numbers()
        return len(jersey_numbers) != len(set(jersey_numbers))

    def add_player(self, player: Player, is_substitute: bool = False):
        """Add a player to the team."""
        if player.team_id != self.id:
            raise ValueError("Player team_id must match team id")
        
        if is_substitute:
            self.substitutes.append(player)
        else:
            self.players.append(player)
        
        self.total_players = len(self.players) + len(self.substitutes)

    def to_dict(self) -> dict:
        """Convert team to dictionary for serialization."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "short_name": self.short_name,
            "logo_url": self.logo_url,
            "manager": self.manager,
            "head_coach": self.head_coach,
            "assistant_coach": self.assistant_coach,
            "total_players": self.total_players,
            "season": self.season,
            "created_date": self.created_date.isoformat(),
            "players": [player.to_dict() for player in self.players],
            "substitutes": [player.to_dict() for player in self.substitutes]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Team':
        """Create team from dictionary."""
        team = cls(
            id=data["id"],
            full_name=data["full_name"],
            short_name=data["short_name"],
            logo_url=data.get("logo_url"),
            manager=data.get("manager"),
            head_coach=data.get("head_coach"),
            assistant_coach=data.get("assistant_coach"),
            season=data.get("season"),
            created_date=datetime.fromisoformat(data.get("created_date", datetime.utcnow().isoformat())),
            players=[Player.from_dict(p) for p in data.get("players", [])],
            substitutes=[Player.from_dict(s) for s in data.get("substitutes", [])]
        )
        return team
