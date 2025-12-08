"""
Helpers to synchronize match operations with the new FastAPI backend.

This module provides convenience functions for clock control and match
operations, delegating to the BackendAPI client.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from .backend_api import get_api, BackendAPI

logger = logging.getLogger(__name__)


def control_backend_clock(match_id: str, action: str, current_seconds: int | float | None = None) -> Optional[Dict[str, Any]]:
    """
    Control the backend clock.
    
    Args:
        match_id: The match ID
        action: One of "start", "stop", "pause", "resume"
        current_seconds: Optional time to set (for sync operations)
    
    Returns:
        Clock state dict or None if failed
    """
    if not match_id:
        return None
    
    api = get_api()
    
    # If we have a specific time to set, set it first
    if current_seconds is not None:
        try:
            secs = max(0, int(current_seconds))
            minutes = secs // 60
            seconds = secs % 60
            api.set_clock_time(match_id, minutes, seconds)
        except Exception as exc:
            logger.warning(f"Failed to set clock time: {exc}")
    
    # Now execute the action
    try:
        if action == "start":
            return api.start_clock(match_id)
        elif action == "stop":
            return api.stop_clock(match_id)
        elif action == "pause":
            return api.pause_clock(match_id)
        elif action == "resume":
            return api.resume_clock(match_id)
        else:
            logger.warning(f"Unknown clock action: {action}")
            return None
    except Exception as exc:
        logger.error(f"Clock control failed for {match_id} ({action}): {exc}")
        return None


def sync_clock_time(match_id: str, minutes: int, seconds: int = 0) -> Optional[Dict[str, Any]]:
    """Set the clock to a specific time."""
    if not match_id:
        return None
    return get_api().set_clock_time(match_id, minutes, seconds)


def set_added_time(match_id: str, minutes: int) -> Optional[Dict[str, Any]]:
    """Set stoppage/added time."""
    if not match_id:
        return None
    return get_api().set_added_time(match_id, minutes)


def advance_period(match_id: str) -> Optional[Dict[str, Any]]:
    """Advance to the next period."""
    if not match_id:
        return None
    return get_api().next_period(match_id)


def set_period(match_id: str, period: str) -> Optional[Dict[str, Any]]:
    """Set a specific period."""
    if not match_id:
        return None
    return get_api().set_period(match_id, period)


def get_match_state(match_id: str) -> Optional[Dict[str, Any]]:
    """Get the full match state from backend."""
    if not match_id:
        return None
    return get_api().get_match(match_id)


def get_match_snapshot(match_id: str) -> Optional[Dict[str, Any]]:
    """Get the match snapshot for graphics output."""
    if not match_id:
        return None
    return get_api().get_match_snapshot(match_id)


def create_backend_match(match_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a match in the backend from desktop app match data.
    
    Converts the desktop app's match_data format to the backend's MatchCreate format
    and creates the match via the API.
    
    Args:
        match_data: Match data from desktop app get_match_data()
        
    Returns:
        Created match data from backend, or None if failed
    """
    try:
        home_team = match_data.get("home_team", {})
        away_team = match_data.get("away_team", {})
        
        # Extract team IDs
        home_team_id = home_team.get("id", "home")
        away_team_id = away_team.get("id", "away")
        
        # Extract formations
        home_formation = home_team.get("formation")
        away_formation = away_team.get("formation")
        
        # Convert playing_11 to lineup format
        def convert_lineup(players: List[Dict], team_side: str) -> List[Dict]:
            lineup = []
            for i, p in enumerate(players or []):
                lineup.append({
                    "player_id": p.get("id", f"{team_side}_{i}"),
                    "name": p.get("name"),
                    "short_name": p.get("short_name"),
                    "jersey_number": p.get("number") or p.get("jersey_number"),
                    "is_starting": True,
                    "is_captain": p.get("is_captain", False),
                    "position_in_formation": p.get("position"),
                    "team": team_side,
                })
            return lineup
        
        home_lineup = convert_lineup(home_team.get("playing_11", []), "home")
        away_lineup = convert_lineup(away_team.get("playing_11", []), "away")
        
        # Prepare team data for API (backend expects full team objects)
        home_team_data = {
            "id": home_team_id,
            "name": home_team.get("name", "Home Team"),
            "short_name": home_team.get("short_name", "HOME"),
            "logo_path": home_team.get("logo") or home_team.get("logo_url"),
            "primary_color": home_team.get("color_1"),
            "secondary_color": home_team.get("color_2"),
        }
        
        away_team_data = {
            "id": away_team_id,
            "name": away_team.get("name", "Away Team"),
            "short_name": away_team.get("short_name", "AWAY"),
            "logo_path": away_team.get("logo") or away_team.get("logo_url"),
            "primary_color": away_team.get("color_1"),
            "secondary_color": away_team.get("color_2"),
        }
        
        # Get venue if available
        venue = match_data.get("venue")
        fixture_id = match_data.get("fixture_id")
        
        # Call backend API
        result = get_api().create_match(
            home_team=home_team_data,
            away_team=away_team_data,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            fixture_id=fixture_id,
            venue=venue,
        )
        
        if result:
            logger.info(f"Created backend match: {result.get('id')}")
        else:
            logger.error("Failed to create backend match")
            
        return result
        
    except Exception as exc:
        logger.error(f"Error creating backend match: {exc}")
        return None


# Alias for backward compatibility (now properly pushes data)
sync_match_snapshot = create_backend_match


# ============ Event Operations ============

def add_goal(
    match_id: str,
    team: str,
    player_name: Optional[str] = None,
    player_number: Optional[int] = None,
    assist_name: Optional[str] = None,
    assist_number: Optional[int] = None,
    is_own_goal: bool = False,
    is_penalty: bool = False
) -> Optional[Dict[str, Any]]:
    """Add a goal event."""
    if not match_id:
        return None
    
    event_type = "own_goal" if is_own_goal else ("penalty_goal" if is_penalty else "goal")
    
    return get_api().add_event(
        match_id=match_id,
        event_type=event_type,
        team=team,
        player_name=player_name,
        player_number=player_number,
        secondary_player_name=assist_name,
        secondary_player_number=assist_number
    )


def add_card(
    match_id: str,
    team: str,
    card_type: str,  # "yellow" or "red"
    player_name: Optional[str] = None,
    player_number: Optional[int] = None,
    reason: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Add a card event."""
    if not match_id:
        return None
    
    event_type = f"{card_type}_card"
    
    return get_api().add_event(
        match_id=match_id,
        event_type=event_type,
        team=team,
        player_name=player_name,
        player_number=player_number,
        notes=reason
    )


def add_substitution(
    match_id: str,
    team: str,
    player_out_name: Optional[str] = None,
    player_out_number: Optional[int] = None,
    player_in_name: Optional[str] = None,
    player_in_number: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Add a substitution event."""
    if not match_id:
        return None
    
    return get_api().add_event(
        match_id=match_id,
        event_type="substitution",
        team=team,
        player_name=player_out_name,
        player_number=player_out_number,
        secondary_player_name=player_in_name,
        secondary_player_number=player_in_number
    )


def undo_last_event(match_id: str, event_id: int) -> bool:
    """Undo (soft delete) an event."""
    if not match_id:
        return False
    return get_api().undo_event(match_id, event_id)


# ============ Stats Operations ============

def update_stat(match_id: str, team: str, stat: str, delta: int = 1) -> Optional[Dict[str, Any]]:
    """Update a stat counter."""
    if not match_id:
        return None
    return get_api().update_stat(match_id, team, stat, delta)


def increment_shots(match_id: str, team: str, on_target: bool = False) -> Optional[Dict[str, Any]]:
    """Increment shots counter."""
    stat = "shots_on_target" if on_target else "shots"
    return update_stat(match_id, team, stat, 1)


def increment_corners(match_id: str, team: str) -> Optional[Dict[str, Any]]:
    """Increment corners counter."""
    return update_stat(match_id, team, "corners", 1)


def increment_fouls(match_id: str, team: str) -> Optional[Dict[str, Any]]:
    """Increment fouls counter."""
    return update_stat(match_id, team, "fouls", 1)


# ============ Possession Operations ============

def set_kickoff_team(match_id: str, team: str) -> Optional[Dict[str, Any]]:
    """Set the kickoff team."""
    if not match_id:
        return None
    return get_api().set_kickoff_team(match_id, team)


def update_possession(match_id: str, home_pct: int, away_pct: int) -> Optional[Dict[str, Any]]:
    """Update possession percentages."""
    if not match_id:
        return None
    return get_api().update_possession(match_id, home_pct=home_pct, away_pct=away_pct)


# ============ Penalty Shootout Operations ============

def start_shootout(match_id: str, first_team: str) -> Optional[Dict[str, Any]]:
    """Start a penalty shootout."""
    if not match_id:
        return None
    return get_api().start_shootout(match_id, first_team)


def add_penalty_kick(match_id: str, team: str, player_name: str, scored: bool) -> Optional[Dict[str, Any]]:
    """Record a penalty kick."""
    if not match_id:
        return None
    return get_api().add_penalty_kick(match_id, team, player_name, scored)


def undo_penalty_kick(match_id: str, kick_id: int) -> bool:
    """Undo a penalty kick."""
    if not match_id:
        return False
    return get_api().undo_penalty_kick(match_id, kick_id)


# ============ Match Lifecycle ============

def create_match(
    home_team: Dict[str, Any],
    away_team: Dict[str, Any],
    home_lineup: List[Dict[str, Any]],
    away_lineup: List[Dict[str, Any]],
    fixture_id: Optional[str] = None,
    venue: Optional[str] = None,
    competition: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Create a new match in the backend."""
    return get_api().create_match(
        home_team=home_team,
        away_team=away_team,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        fixture_id=fixture_id,
        venue=venue,
        competition=competition
    )


def end_match(match_id: str) -> Optional[Dict[str, Any]]:
    """End a match."""
    if not match_id:
        return None
    return get_api().end_match(match_id)


def reset_match(match_id: str) -> Optional[Dict[str, Any]]:
    """Reset a match to initial state."""
    if not match_id:
        return None
    return get_api().reset_match(match_id)


def check_backend_health() -> bool:
    """Check if the backend is running."""
    return get_api().health_check()

