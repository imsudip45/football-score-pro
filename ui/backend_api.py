"""
New Backend API Client for Desktop App.
Connects to the FastAPI backend at localhost:8000.
"""

import os

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("FSP_BACKEND_URL", "http://127.0.0.1:8000")
# Keep the UI responsive if the backend hangs
TIMEOUT = 5


@dataclass
class Team:
    id: str
    name: str
    short_name: str
    logo_path: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


@dataclass
class Player:
    id: str
    name: str
    number: int
    position: str
    is_captain: bool = False
    is_starting: bool = True


class BackendAPI:
    """Client for the new FastAPI backend."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"
    
    def _get(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(self._url(path), timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"GET {path} failed: {e}")
            return None
    
    def _post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.post(self._url(path), json=data or {}, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"POST {path} failed: {e}")
            return None
    
    def _delete(self, path: str) -> bool:
        try:
            resp = self.session.delete(self._url(path), timeout=TIMEOUT)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"DELETE {path} failed: {e}")
            return False
    
    # ============ Health Check ============
    
    def health_check(self) -> bool:
        """Check if backend is running."""
        try:
            resp = self.session.get(self._url("/"), timeout=2)
            return resp.status_code == 200
        except requests.RequestException:
            return False
    
    # ============ Match Management ============
    
    def create_match(
        self,
        home_team: Dict[str, Any],
        away_team: Dict[str, Any],
        home_lineup: List[Dict[str, Any]],
        away_lineup: List[Dict[str, Any]],
        fixture_id: Optional[str] = None,
        venue: Optional[str] = None,
        competition: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new match."""
        data = {
            "home_team_id": home_team.get("id", "home"),
            "away_team_id": away_team.get("id", "away"),
            "home_team": home_team,  # Send full team data for backend to store
            "away_team": away_team,  # Send full team data for backend to store
            "home_formation": home_team.get("formation"),
            "away_formation": away_team.get("formation"),
            "home_lineup": home_lineup,
            "away_lineup": away_lineup,
        }
        if fixture_id:
            data["fixture_id"] = fixture_id
        if venue:
            data["venue"] = venue
        if competition:
            data["competition"] = competition
        
        return self._post("/matches", data)
    
    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get match state."""
        return self._get(f"/matches/{match_id}")
    
    def list_matches(self, status: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """List all matches."""
        path = "/matches"
        if status:
            path += f"?status={status}"
        return self._get(path)
    
    def get_match_snapshot(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get full match snapshot for graphics."""
        return self._get(f"/matches/{match_id}/snapshot")
    
    def end_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """End a match."""
        return self._post(f"/matches/{match_id}/end")
    
    def reset_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Reset a match to initial state."""
        return self._post(f"/matches/{match_id}/reset")
    
    # ============ Clock Control ============
    
    def get_clock(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get current clock state."""
        return self._get(f"/matches/{match_id}/clock")
    
    def start_clock(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Start the clock."""
        return self._post(f"/matches/{match_id}/clock/start")
    
    def pause_clock(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Pause the clock."""
        return self._post(f"/matches/{match_id}/clock/pause")
    
    def resume_clock(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Resume the clock from pause."""
        return self._post(f"/matches/{match_id}/clock/resume")
    
    def stop_clock(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Stop the clock."""
        return self._post(f"/matches/{match_id}/clock/stop")
    
    def set_clock_time(self, match_id: str, minutes: int, seconds: int = 0) -> Optional[Dict[str, Any]]:
        """Manually set clock time."""
        return self._post(f"/matches/{match_id}/clock/set-time", {"minutes": minutes, "seconds": seconds})
    
    def set_added_time(self, match_id: str, minutes: int) -> Optional[Dict[str, Any]]:
        """Set stoppage/added time."""
        return self._post(f"/matches/{match_id}/clock/added-time", {"minutes": minutes})
    
    def next_period(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Advance to next period."""
        return self._post(f"/matches/{match_id}/clock/next-period")
    
    def set_period(self, match_id: str, period: str) -> Optional[Dict[str, Any]]:
        """Set specific period."""
        return self._post(f"/matches/{match_id}/clock/set-period", {"period": period})
    
    # ============ Events ============
    
    def add_event(
        self,
        match_id: str,
        event_type: str,
        team: str,
        player_name: Optional[str] = None,
        player_number: Optional[int] = None,
        secondary_player_name: Optional[str] = None,
        secondary_player_number: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Add a match event (goal, card, sub, etc.)."""
        data = {
            "event_type": event_type,
            "team": team,
        }
        if player_name:
            data["player_name"] = player_name
        if player_number is not None:
            data["player_number"] = player_number
        if secondary_player_name:
            data["secondary_player_name"] = secondary_player_name
        if secondary_player_number is not None:
            data["secondary_player_number"] = secondary_player_number
        if notes:
            data["notes"] = notes
        
        return self._post(f"/matches/{match_id}/events", data)
    
    def get_events(self, match_id: str, include_deleted: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get all events for a match."""
        path = f"/matches/{match_id}/events"
        if include_deleted:
            path += "?include_deleted=true"
        return self._get(path)
    
    def undo_event(self, match_id: str, event_id: int) -> bool:
        """Soft delete an event (undo)."""
        return self._delete(f"/matches/{match_id}/events/{event_id}")
    
    # ============ Stats ============
    
    def get_stats(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get match statistics."""
        return self._get(f"/matches/{match_id}/stats")
    
    def update_stat(
        self,
        match_id: str,
        team: str,
        stat: str,
        delta: int
    ) -> Optional[Dict[str, Any]]:
        """Update a stat counter (increment/decrement)."""
        return self._post(f"/matches/{match_id}/stats", {
            "team": team,
            "stat": stat,
            "delta": delta
        })
    
    # ============ Possession ============
    
    def get_possession(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get possession state."""
        return self._get(f"/matches/{match_id}/possession")
    
    def update_possession(
        self,
        match_id: str,
        current_team: Optional[str] = None,
        home_pct: Optional[int] = None,
        away_pct: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update possession."""
        data = {}
        if current_team is not None:
            data["current_team"] = current_team
        if home_pct is not None:
            data["home_pct"] = home_pct
        if away_pct is not None:
            data["away_pct"] = away_pct
        return self._post(f"/matches/{match_id}/possession", data)
    
    def set_kickoff_team(self, match_id: str, team: str) -> Optional[Dict[str, Any]]:
        """Set kickoff team."""
        return self._post(f"/matches/{match_id}/possession/kickoff", {"team": team})
    
    # ============ Penalty Shootout ============
    
    def get_penalties(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get penalty shootout state."""
        return self._get(f"/matches/{match_id}/penalties")
    
    def start_shootout(self, match_id: str, first_team: str) -> Optional[Dict[str, Any]]:
        """Start penalty shootout."""
        return self._post(f"/matches/{match_id}/penalties/start", {"first_team": first_team})
    
    def add_penalty_kick(
        self,
        match_id: str,
        team: str,
        player_name: str,
        scored: bool
    ) -> Optional[Dict[str, Any]]:
        """Record a penalty kick."""
        return self._post(f"/matches/{match_id}/penalties/kick", {
            "team": team,
            "player_name": player_name,
            "scored": scored
        })
    
    def undo_penalty_kick(self, match_id: str, kick_id: int) -> bool:
        """Undo last penalty kick."""
        return self._delete(f"/matches/{match_id}/penalties/{kick_id}")
    
    # ============ Teams (Reference Data) ============
    
    def get_teams(self) -> Optional[List[Dict[str, Any]]]:
        """Get all teams."""
        return self._get("/teams")
    
    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific team."""
        return self._get(f"/teams/{team_id}")
    
    def create_team(self, team_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new team."""
        return self._post("/teams", team_data)
    
    # ============ Fixtures ============
    
    def get_fixtures(self) -> Optional[List[Dict[str, Any]]]:
        """Get all local fixtures."""
        return self._get("/fixtures")
    
    def get_fixture(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific local fixture."""
        return self._get(f"/fixtures/{fixture_id}")
    
    def load_fixtures_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load fixtures from a JSON file."""
        return self._post("/fixtures/load", {"file_path": file_path})
    
    # ============ Cloud Fixtures ============
    
    def get_cloud_tournaments(self) -> Optional[List[Dict[str, Any]]]:
        """Get tournaments from cloud backend."""
        return self._get("/fixtures/cloud/tournaments")
    
    def get_cloud_tournament(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Get tournament details with fixtures from cloud."""
        return self._get(f"/fixtures/cloud/tournaments/{tournament_id}")
    
    def get_cloud_fixtures(self, tournament_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get fixtures from cloud backend."""
        path = "/fixtures/cloud/fixtures"
        if tournament_id:
            path += f"?tournament_id={tournament_id}"
        return self._get(path)
    
    def get_cloud_fixture(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get fixture details from cloud (with teams and lineups)."""
        return self._get(f"/fixtures/cloud/fixtures/{fixture_id}")
    
    def get_cloud_teams(self) -> Optional[List[Dict[str, Any]]]:
        """Get teams from cloud backend."""
        return self._get("/fixtures/cloud/teams")
    
    def load_fixture_from_cloud(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a fixture from cloud into local database.
        Returns the fixture data ready for match creation.
        """
        return self._post("/fixtures/cloud/load", {"fixture_id": fixture_id})
    
    def create_match_from_cloud_fixture(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """
        Load fixture from cloud and immediately create a match.
        Convenience method that combines load + create.
        """
        # First load the fixture
        load_result = self.load_fixture_from_cloud(fixture_id)
        if not load_result or not load_result.get("fixture"):
            return None
        
        fixture = load_result["fixture"]
        
        # Create match from loaded fixture data
        return self.create_match(
            home_team=fixture["home_team"],
            away_team=fixture["away_team"],
            home_lineup=fixture.get("home_lineup", []),
            away_lineup=fixture.get("away_lineup", []),
            fixture_id=fixture["id"],
            venue=fixture.get("venue"),
            competition=fixture.get("tournament", {}).get("name")
        )


# Global singleton instance
_api_instance: Optional[BackendAPI] = None


def get_api() -> BackendAPI:
    """Get or create the global API instance."""
    global _api_instance
    if _api_instance is None:
        _api_instance = BackendAPI()
    return _api_instance
