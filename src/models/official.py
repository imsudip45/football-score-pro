"""
Official Model for Football Score Pro 2.0
Represents match officials, commentators, and hosts
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class OfficialPosition(Enum):
    """Enumeration of official positions"""
    # Match Officials
    REFEREE = "referee"
    LINESMAN_1 = "linesman_1"
    LINESMAN_2 = "linesman_2"
    FOURTH_OFFICIAL = "fourth_official"
    VAR_REFEREE = "var_referee"
    
    # Commentators
    COMMENTATOR_1 = "commentator_1"
    COMMENTATOR_2 = "commentator_2"
    COMMENTATOR_3 = "commentator_3"
    COMMENTATOR_4 = "commentator_4"
    COMMENTATOR_5 = "commentator_5"
    COMMENTATOR_6 = "commentator_6"
    
    # Hosts
    HOST_1 = "host_1"
    HOST_2 = "host_2"
    HOST_3 = "host_3"


class OfficialType(Enum):
    """Type of official"""
    REFEREE = "referee"
    LINESMAN = "linesman"
    FOURTH_OFFICIAL = "fourth_official"
    VAR_REFEREE = "var_referee"
    COMMENTATOR = "commentator"
    HOST = "host"
    GUEST = "guest"


@dataclass
class Official:
    """
    Represents a match official, commentator, or host
    
    Attributes:
        id: Unique identifier (UUID)
        full_name: Full name of the official
        short_name: Short/display name
        official_type: Type of official (referee, commentator, host, etc.)
        photo_url: Optional URL/path to photo
        nationality: Optional nationality
        experience: Optional experience description
        fifa_qualified: Whether the official is FIFA qualified
    """
    id: str
    full_name: str
    short_name: str
    official_type: OfficialType
    photo_url: Optional[str] = None
    nationality: Optional[str] = None
    experience: Optional[str] = None
    fifa_qualified: bool = False
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.full_name} ({self.official_type.value})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "short_name": self.short_name,
            "official_type": self.official_type.value,
            "photo_url": self.photo_url,
            "nationality": self.nationality,
            "experience": self.experience,
            "fifa_qualified": self.fifa_qualified
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Official':
        """Create Official from dictionary"""
        official_type = data.get("official_type", "")
        if isinstance(official_type, str):
            official_type = OfficialType(official_type)
        
        return cls(
            id=data.get("id", ""),
            full_name=data.get("full_name", ""),
            short_name=data.get("short_name", ""),
            official_type=official_type,
            photo_url=data.get("photo_url"),
            nationality=data.get("nationality"),
            experience=data.get("experience"),
            fifa_qualified=data.get("fifa_qualified", False)
        )


@dataclass
class OfficialsPool:
    """
    Represents a pool of available officials for selection
    
    Attributes:
        tournament_id: ID of the tournament this pool belongs to
        referees: List of referee officials
        linesmen: List of linesman officials
        fourth_officials: List of fourth official officials
        var_referees: List of VAR referee officials
        commentators: List of commentator officials
        hosts: List of host officials
    """
    tournament_id: Optional[str] = None
    referees: list[Official] = field(default_factory=list)
    linesmen: list[Official] = field(default_factory=list)
    fourth_officials: list[Official] = field(default_factory=list)
    var_referees: list[Official] = field(default_factory=list)
    commentators: list[Official] = field(default_factory=list)
    hosts: list[Official] = field(default_factory=list)
    
    def get_by_type(self, official_type: OfficialType) -> list[Official]:
        """Get officials by type"""
        mapping = {
            OfficialType.REFEREE: self.referees,
            OfficialType.LINESMAN: self.linesmen,
            OfficialType.FOURTH_OFFICIAL: self.fourth_officials,
            OfficialType.VAR_REFEREE: self.var_referees,
            OfficialType.COMMENTATOR: self.commentators,
            OfficialType.HOST: self.hosts
        }
        return mapping.get(official_type, [])
    
    def get_all(self) -> list[Official]:
        """Get all officials in the pool"""
        return (
            self.referees + 
            self.linesmen + 
            self.fourth_officials + 
            self.var_referees + 
            self.commentators + 
            self.hosts
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "tournament_id": self.tournament_id,
            "referees": [o.to_dict() for o in self.referees],
            "linesmen": [o.to_dict() for o in self.linesmen],
            "fourth_officials": [o.to_dict() for o in self.fourth_officials],
            "var_referees": [o.to_dict() for o in self.var_referees],
            "commentators": [o.to_dict() for o in self.commentators],
            "hosts": [o.to_dict() for o in self.hosts]
        }

