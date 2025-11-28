"""Service for managing formation layout positions."""

from typing import Dict, Optional, Tuple
from ..services.interfaces import IFormationLayoutService
from ..events.match_events import FormationPositionChangedEvent


class FormationLayoutService(IFormationLayoutService):
    """Service for managing formation layout positions per player per side."""

    def __init__(self, event_bus):
        """Initialize the formation layout service.

        Args:
            event_bus: Event bus for publishing events
        """
        self.event_bus = event_bus
        self._positions = {}  # team_id -> side -> player_name -> (x, y)

    def save_player_position(self, team_id: str, side: str, player_name: str, x: int, y: int) -> None:
        """Save player position in formation.

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_name: Player name
            x: X coordinate
            y: Y coordinate
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        # Initialize nested dictionaries if needed
        if team_id not in self._positions:
            self._positions[team_id] = {}
        if side not in self._positions[team_id]:
            self._positions[team_id][side] = {}

        # Check if position changed
        current_position = self._positions[team_id][side].get(player_name)
        if current_position != (x, y):
            self._positions[team_id][side][player_name] = (x, y)

            # Publish event to notify subscribers
            event = FormationPositionChangedEvent(
                team_id=team_id,
                side=side,
                player_name=player_name,
                x=x,
                y=y,
                position_changed=True
            )
            self.event_bus.publish("formation_position_changed", event)

    def get_player_position(self, team_id: str, side: str, player_name: str) -> Optional[Tuple[int, int]]:
        """Get saved player position.

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_name: Player name

        Returns:
            (x, y) tuple if position exists, None otherwise
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        return self._positions.get(team_id, {}).get(side, {}).get(player_name)

    def get_all_positions(self, team_id: str, side: str) -> Dict[str, Tuple[int, int]]:
        """Get all saved positions for team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"

        Returns:
            Dictionary of player_name -> (x, y)
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        return self._positions.get(team_id, {}).get(side, {}).copy()

    def clear_positions(self, team_id: str, side: str) -> None:
        """Clear all positions for team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        if team_id in self._positions and side in self._positions[team_id]:
            players_cleared = list(self._positions[team_id][side].keys())
            self._positions[team_id][side].clear()

            # Publish event for each cleared position
            for player_name in players_cleared:
                event = FormationPositionChangedEvent(
                    team_id=team_id,
                    side=side,
                    player_name=player_name,
                    x=0,
                    y=0,
                    position_changed=False,
                    position_cleared=True
                )
                self.event_bus.publish("formation_position_changed", event)

    def clear_all_positions(self) -> None:
        """Clear all saved positions."""
        cleared_positions = []
        for team_id in self._positions:
            for side in self._positions[team_id]:
                for player_name in self._positions[team_id][side]:
                    cleared_positions.append((team_id, side, player_name))

        self._positions.clear()

        # Publish events for all cleared positions
        for team_id, side, player_name in cleared_positions:
            event = FormationPositionChangedEvent(
                team_id=team_id,
                side=side,
                player_name=player_name,
                x=0,
                y=0,
                position_changed=False,
                position_cleared=True
            )
            self.event_bus.publish("formation_position_changed", event)

    def get_teams_with_positions(self) -> set:
        """Get set of team IDs that have positions.

        Returns:
            Set of team IDs with any positions
        """
        return set(self._positions.keys())

    def get_sides_with_positions(self, team_id: str) -> set:
        """Get set of sides that have positions for a team.

        Args:
            team_id: Team ID

        Returns:
            Set of sides ("A", "B") with positions
        """
        if team_id not in self._positions:
            return set()
        return set(self._positions[team_id].keys())

    def has_position(self, team_id: str, side: str, player_name: str) -> bool:
        """Check if a player has a saved position.

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_name: Player name

        Returns:
            True if position exists
        """
        return player_name in self._positions.get(team_id, {}).get(side, {})
