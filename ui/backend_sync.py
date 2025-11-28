"""
Helpers to synchronize match snapshots with the FastAPI backend.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

BACKEND_URL = os.environ.get("PITCH_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def sync_match_snapshot(match_id: str, match_data: Dict[str, Any]) -> None:
    """Send the latest desktop snapshot to the FastAPI backend."""
    if not match_id or not match_data:
        return

    snapshot = _build_snapshot(match_id, match_data)
    try:
        response = requests.post(
            f"{BACKEND_URL}/matches/{match_id}/sync",
            json={"snapshot": snapshot},
            timeout=5,
        )
        response.raise_for_status()
    except Exception as exc:
        print(f"[BackendSync] Failed to sync match {match_id}: {exc}")


def control_backend_clock(match_id: str, action: str, current_seconds: int | float | None = None) -> None:
    """Relay clock start/stop/sync commands to the backend."""
    if not match_id:
        return
    payload: Dict[str, Any] = {"action": action}
    if current_seconds is not None:
        try:
            payload["current_seconds"] = max(0, int(current_seconds))
        except Exception:
            payload["current_seconds"] = 0
    try:
        response = requests.post(
            f"{BACKEND_URL}/matches/{match_id}/clock",
            json=payload,
            timeout=3,
        )
        response.raise_for_status()
    except Exception as exc:
        print(f"[BackendSync] Clock sync failed for {match_id} ({action}): {exc}")


def _build_snapshot(match_id: str, match_data: Dict[str, Any]) -> Dict[str, Any]:
    home_team = _team_payload(match_data.get("home_team", {}), "home")
    away_team = _team_payload(match_data.get("away_team", {}), "away")
    fixture_name = (
        match_data.get("fixture_name")
        or match_data.get("match_name")
        or f"{home_team['name']} vs {away_team['name']}"
    )

    officials = _flatten_officials(match_data.get("officials", {}))
    status = match_data.get("status", "SCHEDULED").upper()
    if status not in {"SCHEDULED", "ACTIVE", "PAUSED", "FINISHED"}:
        status = "SCHEDULED"

    return {
        "id": match_id,
        "fixtureName": fixture_name,
        "venue": match_data.get("venue") or match_data.get("stadium") or "Unknown Venue",
        "status": status,
        "currentPeriod": 0,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeStats": _default_stats(),
        "awayStats": _default_stats(),
        "clock": _default_clock(),
        "events": [],
        "officials": officials,
        "penalties": [],
    }


def _team_payload(team: Dict[str, Any], fallback_id: str) -> Dict[str, Any]:
    name = team.get("name") or team.get("full_name") or fallback_id.title()
    short = team.get("short_name") or team.get("shortName") or name[:3].upper()
    color1 = team.get("color_1") or "#ef4444"
    color2 = team.get("color_2") or "#1d4ed8"
    formation = team.get("formation") or "4-4-2"
    players = []
    for idx, player in enumerate(team.get("players", []), start=1):
        jersey = player.get("jersey_number") or player.get("jersey_no") or idx
        try:
            jersey_int = int(jersey)
        except Exception:
            jersey_int = idx
        players.append(
            {
                "id": str(player.get("id") or f"{fallback_id}-{jersey_int}"),
                "number": jersey_int,
                "name": player.get("name") or player.get("full_name") or f"Player {jersey_int}",
                "position": player.get("position") or "MF",
                "isSub": not player.get("selected", False),
            }
        )

    return {
        "id": team.get("id") or fallback_id,
        "name": name,
        "shortName": short,
        "colors": [color1, color2],
        "kitImage": _extract_kit(team),
        "score": int(team.get("score", 0)),
        "players": players,
        "formation": formation,
    }


def _extract_kit(team: Dict[str, Any]) -> str | None:
    kits = team.get("kits") or []
    if isinstance(kits, list) and kits:
        return kits[0].get("image") or kits[0].get("url")
    if isinstance(kits, dict):
        return kits.get("image") or kits.get("url")
    return team.get("kit_image")


def _flatten_officials(officials: Dict[str, Any]) -> List[str]:
    if isinstance(officials, list):
        return [str(o) for o in officials if o]
    if isinstance(officials, dict):
        values: List[str] = []
        for value in officials.values():
            if isinstance(value, list):
                values.extend([str(v) for v in value if v])
            elif value:
                values.append(str(value))
        return values
    return []


def _default_stats() -> Dict[str, Any]:
    return {
        "possession": 50,
        "shots": 0,
        "shotsOnTarget": 0,
        "corners": 0,
        "fouls": 0,
        "yellowCards": 0,
        "redCards": 0,
    }


def _default_clock() -> Dict[str, Any]:
    return {
        "isRunning": False,
        "startTime": None,
        "elapsedBeforeResume": 0,
        "lastSyncedAt": 0,
        "authority": "LOCAL",
    }

