"""Service for managing side assignments (home/away team selection)."""

from typing import Optional, Dict, Any
from ..services.interfaces import ISideAssignmentService
from ..events.match_events import SideAssignmentChangedEvent


class SideAssignmentService(ISideAssignmentService):
    """Service for managing which teams are assigned to home/away sides."""

    def __init__(self, event_bus):
        """Initialize the side assignment service.

        Args:
            event_bus: Event bus for publishing events
        """
        self.event_bus = event_bus
        self._home_uses_a = True  # Default: home uses side A
        self._team_assignments = {}  # team_id -> side ("A" or "B")

    def set_home_uses_a(self, uses_a: bool) -> None:
        """Set whether home team uses side A.

        Args:
            uses_a: True if home team should use side A, False for side B
        """
        if self._home_uses_a != uses_a:
            self._home_uses_a = uses_a
            # Publish event to notify subscribers
            event = SideAssignmentChangedEvent(
                home_uses_a=uses_a,
                effective_home_team=self.get_effective_home_team(),
                effective_away_team=self.get_effective_away_team()
            )
            self.event_bus.publish("side_assignment_changed", event)

    def get_home_uses_a(self) -> bool:
        """Get whether home team uses side A.

        Returns:
            True if home team uses side A
        """
        return self._home_uses_a

    def get_effective_home_team(self) -> Optional[str]:
        """Get effective home team ID based on current assignment.

        Returns:
            Team ID of the effective home team, or None if not set
        """
        if not self._team_assignments:
            return None

        if self._home_uses_a:
            # Home uses A, so find team assigned to A
            for team_id, side in self._team_assignments.items():
                if side == "A":
                    return team_id
        else:
            # Home uses B, so find team assigned to B
            for team_id, side in self._team_assignments.items():
                if side == "B":
                    return team_id
        return None

    def get_effective_away_team(self) -> Optional[str]:
        """Get effective away team ID based on current assignment.

        Returns:
            Team ID of the effective away team, or None if not set
        """
        if not self._team_assignments:
            return None

        if self._home_uses_a:
            # Home uses A, so away uses B
            for team_id, side in self._team_assignments.items():
                if side == "B":
                    return team_id
        else:
            # Home uses B, so away uses A
            for team_id, side in self._team_assignments.items():
                if side == "A":
                    return team_id
        return None

    def get_side_for_team(self, team_id: str) -> Optional[str]:
        """Get which side (A or B) a team is assigned to.

        Args:
            team_id: Team ID to check

        Returns:
            "A" or "B" if team is assigned, None otherwise
        """
        return self._team_assignments.get(team_id)

    def set_team_side(self, team_id: str, side: str) -> None:
        """Set which side a team is assigned to.

        Args:
            team_id: Team ID
            side: "A" or "B"
        """
        if side not in ["A", "B"]:
            raise ValueError("Side must be 'A' or 'B'")

        # If team is already assigned to a different side, remove the old assignment
        if team_id in self._team_assignments and self._team_assignments[team_id] != side:
            old_side = self._team_assignments[team_id]
            # If this team was the only team on the old side, we need to handle it
            teams_on_old_side = [tid for tid, s in self._team_assignments.items() if s == old_side]
            if len(teams_on_old_side) == 1 and teams_on_old_side[0] == team_id:
                # This was the only team on that side, but we're moving it
                # The side will become empty, which is fine
                pass

        self._team_assignments[team_id] = side

        # Publish event to notify subscribers
        event = SideAssignmentChangedEvent(
            home_uses_a=self._home_uses_a,
            effective_home_team=self.get_effective_home_team(),
            effective_away_team=self.get_effective_away_team()
        )
        self.event_bus.publish("side_assignment_changed", event)

    def clear_assignment(self) -> None:
        """Clear side assignments."""
        self._team_assignments.clear()
        self._home_uses_a = True

        # Publish event to notify subscribers
        event = SideAssignmentChangedEvent(
            home_uses_a=True,
            effective_home_team=None,
            effective_away_team=None
        )
        self.event_bus.publish("side_assignment_changed", event)

    def get_team_assignments(self) -> Dict[str, str]:
        """Get all team assignments.

        Returns:
            Dictionary of team_id -> side
        """
        return self._team_assignments.copy()
