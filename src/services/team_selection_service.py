"""Service for managing team player selection state."""

from typing import Set, Dict, Any
from ..services.interfaces import ITeamSelectionService
from ..events.match_events import TeamSelectionChangedEvent


class TeamSelectionService(ITeamSelectionService):
    """Service for managing player selection state per team per side."""

    def __init__(self, event_bus):
        """Initialize the team selection service.

        Args:
            event_bus: Event bus for publishing events
        """
        self.event_bus = event_bus
        self._max_players = 11  # Maximum players per team
        self._selections = {}  # team_id -> side -> set of player_ids

    def set_selected_players(self, team_id: str, side: str, player_ids: set) -> None:
        """Set selected players for a team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_ids: Set of selected player IDs
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        # Validate selection count
        if len(player_ids) > self._max_players:
            raise ValueError(f"Cannot select more than {self._max_players} players")

        # Store the selection
        if team_id not in self._selections:
            self._selections[team_id] = {}
        self._selections[team_id][side] = player_ids.copy()

        # Publish event to notify subscribers
        event = TeamSelectionChangedEvent(
            team_id=team_id,
            side=side,
            selected_player_ids=player_ids.copy(),
            selection_count=len(player_ids),
            can_select_more=len(player_ids) < self._max_players
        )
        self.event_bus.publish("team_selection_changed", event)

    def get_selected_players(self, team_id: str, side: str) -> set:
        """Get selected players for a team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"

        Returns:
            Set of selected player IDs
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        return self._selections.get(team_id, {}).get(side, set()).copy()

    def add_selected_player(self, team_id: str, side: str, player_id: str) -> bool:
        """Add a player to selection, returns True if successful (within limit).

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_id: Player ID to add

        Returns:
            True if player was added successfully, False if limit reached
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        current_selection = self.get_selected_players(team_id, side)
        if len(current_selection) >= self._max_players:
            return False  # Cannot add more players

        current_selection.add(player_id)
        self.set_selected_players(team_id, side, current_selection)
        return True

    def remove_selected_player(self, team_id: str, side: str, player_id: str) -> None:
        """Remove a player from selection.

        Args:
            team_id: Team ID
            side: "A" or "B"
            player_id: Player ID to remove
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        current_selection = self.get_selected_players(team_id, side)
        current_selection.discard(player_id)
        self.set_selected_players(team_id, side, current_selection)

    def can_select_more(self, team_id: str, side: str) -> bool:
        """Check if more players can be selected (within 11 limit).

        Args:
            team_id: Team ID
            side: "A" or "B"

        Returns:
            True if more players can be selected
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        current_count = self.get_selection_count(team_id, side)
        return current_count < self._max_players

    def get_selection_count(self, team_id: str, side: str) -> int:
        """Get current selection count for team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"

        Returns:
            Number of selected players
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        return len(self.get_selected_players(team_id, side))

    def clear_selection(self, team_id: str, side: str) -> None:
        """Clear all selections for a team and side.

        Args:
            team_id: Team ID
            side: "A" or "B"
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        self.set_selected_players(team_id, side, set())

    def get_all_selections(self) -> Dict[str, Dict[str, set]]:
        """Get all selections.

        Returns:
            Dictionary of team_id -> side -> set of player_ids
        """
        return {
            team_id: {
                side: players.copy()
                for side, players in sides.items()
            }
            for team_id, sides in self._selections.items()
        }

    def clear_all_selections(self) -> None:
        """Clear all selections for all teams."""
        self._selections.clear()

    def get_teams_with_selections(self) -> set:
        """Get set of team IDs that have selections.

        Returns:
            Set of team IDs with any selections
        """
        return set(self._selections.keys())
