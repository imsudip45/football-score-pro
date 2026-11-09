"""Match state and the rules that change it.

Everything here is plain Python with no web framework, so it can be tested
directly. A match is stored as one JSON-serialisable dict.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Periods in order. Minutes are where each playing period starts and ends on
# the match clock (the clock counts total match time, like a broadcast clock).
PERIODS = ["1H", "HT", "2H", "ET1", "ET2", "PEN", "FT"]
PERIOD_START_MINUTE = {"1H": 0, "HT": 45, "2H": 45, "ET1": 90, "ET2": 105, "PEN": 120, "FT": 120}
PERIOD_END_MINUTE = {"1H": 45, "2H": 90, "ET1": 105, "ET2": 120}
PLAYING_PERIODS = set(PERIOD_END_MINUTE)

STAT_FIELDS = ["shots", "shots_on_target", "corners", "fouls", "offsides", "free_kicks"]
GOAL_EVENTS = {"goal", "penalty_goal", "penalty_scored"}
YELLOW_EVENTS = {"yellow_card", "second_yellow"}
RED_EVENTS = {"red_card", "second_yellow"}

MATCH_STATUSES = {"created", "live", "halftime", "finished", "abandoned"}


class MatchError(ValueError):
    """Raised for a request that doesn't make sense for the match's state."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _side(team: Any) -> str:
    if team not in ("home", "away"):
        raise MatchError("team must be 'home' or 'away'")
    return team


def _other(team: str) -> str:
    return "away" if team == "home" else "home"


# ---------------------------------------------------------------- creation


def _normalize_team(team: Optional[Dict[str, Any]], fallback_id: str, default_name: str) -> Dict[str, Any]:
    team = dict(team or {})
    team.setdefault("id", fallback_id)
    name = team.get("name") or team.get("full_name") or team.get("short_name") or default_name
    team["name"] = name
    team.setdefault("short_name", name[:3].upper())
    if not team.get("logo_path") and team.get("logo_url"):
        team["logo_path"] = team["logo_url"]
    team.pop("players", None)
    return team


def _normalize_lineup(players: Optional[List[Dict[str, Any]]], side: str) -> List[Dict[str, Any]]:
    """Accept both the dashboard's player shape and the desktop app's lineup shape."""
    lineup = []
    for i, p in enumerate(players or []):
        p = p or {}
        number = p.get("jersey_number", p.get("number"))
        lineup.append(
            {
                "player_id": str(p.get("player_id") or p.get("id") or f"{side}_{i + 1}"),
                "team": side,
                "name": p.get("name") or p.get("full_name"),
                "short_name": p.get("short_name"),
                "jersey_number": int(number) if isinstance(number, (int, float, str)) and str(number).isdigit() else None,
                "is_starting": bool(p.get("is_starting", True)),
                "is_captain": bool(p.get("is_captain", False)),
                "position_in_formation": p.get("position_in_formation") or p.get("position"),
                "formation_x": p.get("formation_x"),
                "formation_y": p.get("formation_y"),
            }
        )
    return lineup


def new_clock() -> Dict[str, Any]:
    return {
        "status": "stopped",
        "period": "1H",
        "base_seconds": 0.0,  # match-clock seconds banked while not running
        "running_since": None,  # time.time() when the clock last started
        "real_elapsed_seconds": 0.0,
        "added_time_minutes": 0,
    }


def new_match(payload: Dict[str, Any]) -> Dict[str, Any]:
    home_team = _normalize_team(payload.get("home_team"), payload.get("home_team_id") or "home", "Home Team")
    away_team = _normalize_team(payload.get("away_team"), payload.get("away_team_id") or "away", "Away Team")
    if home_team["id"] == away_team["id"]:
        raise MatchError("home and away teams must be different")
    return {
        "match": {
            "id": str(uuid.uuid4()),
            "fixture_id": payload.get("fixture_id"),
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "home_formation": payload.get("home_formation") or home_team.get("formation"),
            "away_formation": payload.get("away_formation") or away_team.get("formation"),
            "home_kit_id": payload.get("home_kit_id"),
            "away_kit_id": payload.get("away_kit_id"),
            "status": "created",
            "current_period": "1H",
            "home_score": 0,
            "away_score": 0,
            "winner": None,
            "venue": payload.get("venue"),
            "competition": payload.get("competition"),
            "created_at": now_iso(),
            "started_at": None,
            "finished_at": None,
        },
        "home_team": home_team,
        "away_team": away_team,
        "home_lineup": _normalize_lineup(payload.get("home_lineup"), "home"),
        "away_lineup": _normalize_lineup(payload.get("away_lineup"), "away"),
        "clock": new_clock(),
        "possession": {"home_ms": 0, "away_ms": 0, "home_pct": 50, "away_pct": 50,
                       "current_team": None, "kickoff_team": None, "since": None, "manual": False},
        "stats": {f"{side}_{f}": 0 for side in ("home", "away") for f in STAT_FIELDS},
        "card_adjustments": {"home_yellow_cards": 0, "away_yellow_cards": 0,
                             "home_red_cards": 0, "away_red_cards": 0},
        "events": [],
        "next_event_id": 1,
        "penalty_shootout": None,
        "next_kick_id": 1,
    }


def reset_match(m: Dict[str, Any]) -> None:
    fresh = new_match({
        "home_team": m["home_team"], "away_team": m["away_team"],
        "home_lineup": m["home_lineup"], "away_lineup": m["away_lineup"],
        "fixture_id": m["match"].get("fixture_id"), "venue": m["match"].get("venue"),
        "competition": m["match"].get("competition"),
        "home_formation": m["match"].get("home_formation"), "away_formation": m["match"].get("away_formation"),
    })
    fresh["match"]["id"] = m["match"]["id"]
    fresh["match"]["created_at"] = m["match"]["created_at"]
    m.clear()
    m.update(fresh)


# ------------------------------------------------------------------- clock


def clock_seconds(m: Dict[str, Any], at: Optional[float] = None) -> float:
    c = m["clock"]
    seconds = c["base_seconds"]
    if c["status"] == "running" and c["running_since"] is not None:
        seconds += (at or time.time()) - c["running_since"]
    return max(0.0, seconds)


def clock_view(m: Dict[str, Any]) -> Dict[str, Any]:
    c = m["clock"]
    secs = int(clock_seconds(m))
    minute, second = divmod(secs, 60)
    period = c["period"]
    end = PERIOD_END_MINUTE.get(period)
    real = c["real_elapsed_seconds"]
    if c["status"] == "running" and c["running_since"] is not None:
        real += time.time() - c["running_since"]
    return {
        "status": c["status"],
        "period": period,
        "display_minute": minute,
        "display_second": second,
        "real_elapsed_seconds": round(real, 1),
        "added_time_minutes": c["added_time_minutes"],
        "is_added_time": bool(end is not None and minute >= end),
    }


def _bank_clock(m: Dict[str, Any]) -> None:
    """Fold running time into base_seconds and stop counting."""
    c = m["clock"]
    if c["status"] == "running" and c["running_since"] is not None:
        elapsed = time.time() - c["running_since"]
        c["base_seconds"] += elapsed
        c["real_elapsed_seconds"] += elapsed
    c["running_since"] = None
    _bank_possession(m)


def start_clock(m: Dict[str, Any]) -> None:
    c = m["clock"]
    if m["match"]["status"] in ("finished", "abandoned"):
        raise MatchError("match is finished")
    if c["period"] == "HT":
        # Starting the clock at half-time means the second half has kicked off
        c["period"] = "2H"
        m["match"]["current_period"] = "2H"
    if c["period"] not in PLAYING_PERIODS:
        raise MatchError(f"clock can't run during {c['period']}")
    if c["status"] == "running":
        return
    c["status"] = "running"
    c["running_since"] = time.time()
    m["possession"]["since"] = c["running_since"] if m["possession"]["current_team"] else None
    match = m["match"]
    match["status"] = "live"
    match["started_at"] = match["started_at"] or now_iso()


def pause_clock(m: Dict[str, Any]) -> None:
    if m["clock"]["status"] != "running":
        return
    _bank_clock(m)
    m["clock"]["status"] = "paused"


def resume_clock(m: Dict[str, Any]) -> None:
    start_clock(m)


def stop_clock(m: Dict[str, Any]) -> None:
    _bank_clock(m)
    m["clock"]["status"] = "stopped"


def set_clock_time(m: Dict[str, Any], minutes: int, seconds: int = 0) -> None:
    if minutes < 0 or not 0 <= seconds < 60:
        raise MatchError("minutes must be >= 0 and seconds 0-59")
    c = m["clock"]
    running = c["status"] == "running"
    _bank_clock(m)
    c["base_seconds"] = float(minutes * 60 + seconds)
    if running:
        c["running_since"] = time.time()
        if m["possession"]["current_team"]:
            m["possession"]["since"] = c["running_since"]


def set_added_time(m: Dict[str, Any], minutes: int) -> None:
    if minutes < 0:
        raise MatchError("added time can't be negative")
    m["clock"]["added_time_minutes"] = int(minutes)


def set_period(m: Dict[str, Any], period: str) -> None:
    if period not in PERIODS:
        raise MatchError(f"period must be one of {', '.join(PERIODS)}")
    stop_clock(m)
    c = m["clock"]
    c["period"] = period
    c["added_time_minutes"] = 0
    c["base_seconds"] = float(PERIOD_START_MINUTE[period] * 60)
    match = m["match"]
    match["current_period"] = period
    if period == "HT":
        match["status"] = "halftime"
    elif period == "FT":
        finish_match(m)
    elif match["status"] in ("halftime", "created") and match["started_at"]:
        match["status"] = "live"
    if period == "PEN" and not m["penalty_shootout"]:
        start_shootout(m, m["possession"].get("kickoff_team") or "home")


def next_period(m: Dict[str, Any]) -> None:
    current = m["clock"]["period"]
    idx = PERIODS.index(current)
    if idx == len(PERIODS) - 1:
        raise MatchError("match is already at full time")
    set_period(m, PERIODS[idx + 1])


def finish_match(m: Dict[str, Any]) -> None:
    _bank_clock(m)
    m["clock"]["status"] = "stopped"
    m["clock"]["period"] = "FT"
    match = m["match"]
    match["current_period"] = "FT"
    match["status"] = "finished"
    match["finished_at"] = match["finished_at"] or now_iso()
    _recalculate(m)
    if match["home_score"] != match["away_score"]:
        match["winner"] = "home" if match["home_score"] > match["away_score"] else "away"
    elif m["penalty_shootout"] and m["penalty_shootout"].get("winner"):
        match["winner"] = m["penalty_shootout"]["winner"]
    else:
        match["winner"] = "draw"


# ------------------------------------------------------------------ events


def add_event(m: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    event_type = (data.get("event_type") or "").strip()
    if not event_type:
        raise MatchError("event_type is required")
    team = _side(data.get("team"))
    view = clock_view(m)
    event = {
        "id": m["next_event_id"],
        "event_type": event_type,
        "team": team,
        "player_name": data.get("player_name"),
        "player_number": data.get("player_number"),
        "secondary_player_name": data.get("secondary_player_name"),
        "secondary_player_number": data.get("secondary_player_number"),
        # Football convention: an event in the 23rd minute (22:xx) shows as 23'
        "display_minute": view["display_minute"] + 1,
        "period": view["period"],
        "notes": data.get("notes"),
        "created_at": now_iso(),
        "is_deleted": False,
    }
    m["next_event_id"] += 1
    m["events"].append(event)
    _recalculate(m)
    return event


def undo_event(m: Dict[str, Any], event_id: int) -> None:
    for event in m["events"]:
        if event["id"] == event_id and not event["is_deleted"]:
            event["is_deleted"] = True
            _recalculate(m)
            return
    raise KeyError(f"event {event_id} not found")


def visible_events(m: Dict[str, Any], include_deleted: bool = False) -> List[Dict[str, Any]]:
    return [e for e in m["events"] if include_deleted or not e["is_deleted"]]


def _recalculate(m: Dict[str, Any]) -> None:
    """Scores and card counts always come from the event log, so undo is exact."""
    score = {"home": 0, "away": 0}
    for e in visible_events(m):
        if e["event_type"] in GOAL_EVENTS:
            score[e["team"]] += 1
        elif e["event_type"] == "own_goal":
            score[_other(e["team"])] += 1
    m["match"]["home_score"] = score["home"]
    m["match"]["away_score"] = score["away"]


# ------------------------------------------------------------------- stats


def stats_row(m: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(m["stats"])
    for side in ("home", "away"):
        events = [e for e in visible_events(m) if e["team"] == side]
        row[f"{side}_yellow_cards"] = max(0, sum(e["event_type"] in YELLOW_EVENTS for e in events)
                                          + m["card_adjustments"][f"{side}_yellow_cards"])
        row[f"{side}_red_cards"] = max(0, sum(e["event_type"] in RED_EVENTS for e in events)
                                       + m["card_adjustments"][f"{side}_red_cards"])
    return row


def stats_by_team(m: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    row = stats_row(m)
    fields = STAT_FIELDS + ["yellow_cards", "red_cards"]
    return {side: {f: row[f"{side}_{f}"] for f in fields} for side in ("home", "away")}


def update_stat(m: Dict[str, Any], team: str, stat: str, delta: int) -> None:
    team = _side(team)
    if stat in ("yellow_cards", "red_cards"):
        m["card_adjustments"][f"{team}_{stat}"] += int(delta)
        return
    if stat not in STAT_FIELDS:
        raise MatchError(f"unknown stat '{stat}'")
    key = f"{team}_{stat}"
    m["stats"][key] = max(0, m["stats"][key] + int(delta))


# -------------------------------------------------------------- possession


def _bank_possession(m: Dict[str, Any]) -> None:
    """Add the time since `since` to the team in possession and stop counting."""
    p = m["possession"]
    if p["current_team"] and p["since"] is not None:
        p[f"{p['current_team']}_ms"] += int((time.time() - p["since"]) * 1000)
    p["since"] = None


def possession_view(m: Dict[str, Any]) -> Dict[str, Any]:
    p = m["possession"]
    home_ms, away_ms = p["home_ms"], p["away_ms"]
    if p["current_team"] and p["since"] is not None:
        live = int((time.time() - p["since"]) * 1000)
        if p["current_team"] == "home":
            home_ms += live
        else:
            away_ms += live
    if p["manual"] or home_ms + away_ms == 0:
        home_pct, away_pct = p["home_pct"], p["away_pct"]
    else:
        home_pct = round(100 * home_ms / (home_ms + away_ms))
        away_pct = 100 - home_pct
    return {"home_ms": home_ms, "away_ms": away_ms, "home_pct": home_pct, "away_pct": away_pct,
            "current_team": p["current_team"], "kickoff_team": p["kickoff_team"]}


def update_possession(m: Dict[str, Any], data: Dict[str, Any]) -> None:
    p = m["possession"]
    if "current_team" in data:
        team = data["current_team"]
        if team is not None:
            _side(team)
        _bank_possession(m)
        p["current_team"] = team
        p["since"] = time.time() if (team and m["clock"]["status"] == "running") else None
    home_pct, away_pct = data.get("home_pct"), data.get("away_pct")
    if home_pct is not None or away_pct is not None:
        if home_pct is None:
            home_pct = 100 - int(away_pct)
        if away_pct is None:
            away_pct = 100 - int(home_pct)
        if not (0 <= int(home_pct) <= 100 and 0 <= int(away_pct) <= 100):
            raise MatchError("possession percentages must be between 0 and 100")
        p["home_pct"], p["away_pct"], p["manual"] = int(home_pct), int(away_pct), True


def set_kickoff_team(m: Dict[str, Any], team: str) -> None:
    team = _side(team)
    m["possession"]["kickoff_team"] = team
    update_possession(m, {"current_team": team})


# --------------------------------------------------------------- penalties


def start_shootout(m: Dict[str, Any], first_team: str) -> None:
    first_team = _side(first_team)
    if m["penalty_shootout"] and m["penalty_shootout"]["kicks"]:
        raise MatchError("a shootout with kicks already exists")
    m["penalty_shootout"] = {"is_active": True, "first_team": first_team, "kicks": []}


def add_kick(m: Dict[str, Any], team: str, player_name: str, scored: bool) -> Dict[str, Any]:
    team = _side(team)
    if not m["penalty_shootout"]:
        start_shootout(m, team)
    shootout = m["penalty_shootout"]
    if shootout_view(m)["winner"]:
        raise MatchError("the shootout is already decided")
    order = sum(1 for k in shootout["kicks"] if k["team"] == team) + 1
    kick = {"id": m["next_kick_id"], "order": order, "team": team,
            "player_name": player_name or "", "scored": bool(scored)}
    m["next_kick_id"] += 1
    shootout["kicks"].append(kick)
    return kick


def undo_kick(m: Dict[str, Any], kick_id: int) -> None:
    shootout = m["penalty_shootout"]
    if shootout:
        for i, kick in enumerate(shootout["kicks"]):
            if kick["id"] == kick_id:
                del shootout["kicks"][i]
                # Renumber that team's kicks so order stays 1..n
                n = 0
                for k in shootout["kicks"]:
                    if k["team"] == kick["team"]:
                        n += 1
                        k["order"] = n
                return
    raise KeyError(f"kick {kick_id} not found")


def shootout_winner(home_kicks: List[Dict], away_kicks: List[Dict]) -> Optional[str]:
    """Best of five, decided early when one side can't catch up, then sudden death."""
    h, a = len(home_kicks), len(away_kicks)
    hs = sum(k["scored"] for k in home_kicks)
    as_ = sum(k["scored"] for k in away_kicks)
    if h <= 5 and a <= 5:
        if hs + (5 - h) < as_:
            return "away"
        if as_ + (5 - a) < hs:
            return "home"
        if h == 5 and a == 5 and hs != as_:
            return "home" if hs > as_ else "away"
        return None
    if h == a and hs != as_:
        return "home" if hs > as_ else "away"
    return None


def shootout_view(m: Dict[str, Any]) -> Dict[str, Any]:
    shootout = m["penalty_shootout"]
    if not shootout:
        return {"is_active": False, "home_scored": 0, "away_scored": 0, "home_kicks": [],
                "away_kicks": [], "current_round": 1, "first_team": "home", "winner": None}
    home = [k for k in shootout["kicks"] if k["team"] == "home"]
    away = [k for k in shootout["kicks"] if k["team"] == "away"]
    winner = shootout_winner(home, away)
    return {
        "is_active": shootout["is_active"] and winner is None,
        "home_scored": sum(k["scored"] for k in home),
        "away_scored": sum(k["scored"] for k in away),
        "home_kicks": home,
        "away_kicks": away,
        "current_round": min(len(home), len(away)) + 1,
        "first_team": shootout["first_team"],
        "winner": winner,
    }


# -------------------------------------------------------------------- views


def full_state(m: Dict[str, Any]) -> Dict[str, Any]:
    """The shape the dashboard calls BackendMatchState."""
    return {
        "match": dict(m["match"]),
        "home_team": m["home_team"],
        "away_team": m["away_team"],
        "home_lineup": m["home_lineup"],
        "away_lineup": m["away_lineup"],
        "clock": clock_view(m),
        "possession": possession_view(m),
        "stats": stats_row(m),
        "events": visible_events(m),
        "penalty_shootout": shootout_view(m) if m["penalty_shootout"] else None,
    }
