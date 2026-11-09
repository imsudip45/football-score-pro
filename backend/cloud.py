"""Calls to outside services: the fixtures server (cloud-backend/) and the
Open-Meteo weather API. Both are optional; the match API works without them."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

CLOUD_URL = os.environ.get("FSP_CLOUD_URL", "http://localhost:3001").rstrip("/")
TIMEOUT = 10


class UpstreamError(RuntimeError):
    """The fixtures server or weather service didn't answer usefully."""


def _absolute(url: Optional[str]) -> Optional[str]:
    """Logos and kits on the fixtures server are relative paths; make them
    absolute so the dashboard and desktop app can load them directly."""
    if url and url.startswith("/"):
        return f"{CLOUD_URL}{url}"
    return url


def cloud_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        resp = requests.get(f"{CLOUD_URL}{path}", params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise UpstreamError(f"fixtures server at {CLOUD_URL} is not reachable") from exc
    if resp.status_code == 404:
        raise KeyError(resp.json().get("error", "not found") if resp.content else "not found")
    if not resp.ok:
        raise UpstreamError(f"fixtures server returned {resp.status_code}")
    return resp.json()


def cloud_post(path: str, body: Dict[str, Any]) -> Any:
    try:
        resp = requests.post(f"{CLOUD_URL}{path}", json=body, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise UpstreamError(f"fixtures server at {CLOUD_URL} is not reachable") from exc
    if resp.status_code == 404:
        raise KeyError("fixture not found on the fixtures server")
    if not resp.ok:
        raise UpstreamError(f"fixtures server returned {resp.status_code}")
    return resp.json()


def fixture_to_local(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Turn a fixtures-server fixture into the local fixture shape the desktop
    app's fixture loader reads (teams carry a combined `players` list)."""
    fixture = dict(detail)
    fixture["tournament_id"] = (detail.get("tournament") or {}).get("id")
    if fixture.get("tournament"):
        fixture["tournament"] = dict(fixture["tournament"], logo_url=_absolute(fixture["tournament"].get("logo_url")))
    for side in ("home", "away"):
        team = dict(detail.get(f"{side}_team") or {})
        team["logo_url"] = _absolute(team.get("logo_url"))
        team["kits"] = [dict(k, image_url=_absolute(k.get("image_url"))) for k in team.get("kits", [])]
        starters = [dict(p, is_starting=True) for p in detail.get(f"{side}_lineup", [])]
        subs = [dict(p, is_starting=False) for p in detail.get(f"{side}_substitutes", [])]
        team["players"] = starters + subs
        fixture[f"{side}_team"] = team
    return fixture


def match_payload_from_fixture(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Build a POST /matches body from a local fixture."""
    payload: Dict[str, Any] = {"fixture_id": fixture.get("id"), "venue": fixture.get("venue"),
                               "competition": (fixture.get("tournament") or {}).get("name")}
    for side in ("home", "away"):
        team = fixture.get(f"{side}_team") or {}
        payload[f"{side}_team"] = {k: v for k, v in team.items() if k not in ("players", "kits")}
        payload[f"{side}_lineup"] = [p for p in team.get("players", []) if p.get("is_starting", True)]
    return payload


# ------------------------------------------------------------------ weather

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def _get_json(url: str, params: Dict[str, Any]) -> Any:
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise UpstreamError("weather service unavailable") from exc


def geocode(name: str) -> Dict[str, Any]:
    data = _get_json("https://geocoding-api.open-meteo.com/v1/search", {"name": name, "count": 1})
    results: List[Dict[str, Any]] = data.get("results") or []
    if not results:
        # Venue names like "Dasharath Stadium, Kathmandu" often only match on the city
        if "," in name:
            return geocode(name.split(",")[-1].strip())
        raise KeyError(f"no location found for '{name}'")
    return results[0]


def weather(latitude: float, longitude: float, date: Optional[str], label: str) -> Dict[str, Any]:
    """Current conditions at a location. `date` is accepted for API
    compatibility but the reading is always the current one."""
    params: Dict[str, Any] = {
        "latitude": latitude, "longitude": longitude, "timezone": "auto",
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code,precipitation",
    }
    data = _get_json("https://api.open-meteo.com/v1/forecast", params)
    cur = data.get("current") or {}
    return {
        "venue": label,
        "date": (cur.get("time") or "")[:10],
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "weather": {
            "temperature": cur.get("temperature_2m"),
            "humidity": cur.get("relative_humidity_2m"),
            "wind_speed": cur.get("wind_speed_10m"),
            "wind_direction": cur.get("wind_direction_10m"),
            "conditions": WEATHER_CODES.get(cur.get("weather_code"), "Unknown"),
            "precipitation": cur.get("precipitation"),
        },
    }
