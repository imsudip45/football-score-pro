"""
Officials Events for Football Score Pro 2.0
Event-driven architecture for officials management
"""

from dataclasses import dataclass
from typing import Optional, List
from ..models.official import Official, OfficialsPool, OfficialType


@dataclass
class OfficialsPoolLoadedEvent:
    """
    Event published when officials pool is loaded
    
    Attributes:
        tournament_id: Optional tournament ID
        pool: The loaded officials pool
        total_officials: Total number of officials in pool
    """
    tournament_id: Optional[str]
    pool: OfficialsPool
    total_officials: int
    
    def __str__(self) -> str:
        return f"OfficialsPoolLoaded(tournament={self.tournament_id}, total={self.total_officials})"


@dataclass
class OfficialAssignedEvent:
    """
    Event published when an official is assigned to a position
    
    Attributes:
        match_id: ID of the match
        position: Position assigned (referee, assistant1, etc.)
        official: The assigned official
    """
    match_id: str
    position: str
    official: Official
    
    def __str__(self) -> str:
        return f"OfficialAssigned(match={self.match_id}, position={self.position}, official={self.official.full_name})"


@dataclass
class OfficialsPoolClearedEvent:
    """
    Event published when officials pool is cleared
    
    Attributes:
        tournament_id: Optional tournament ID
    """
    tournament_id: Optional[str]
    
    def __str__(self) -> str:
        return f"OfficialsPoolCleared(tournament={self.tournament_id})"

