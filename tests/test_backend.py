"""Tests for the match API in backend/."""

import time

import pytest
from fastapi.testclient import TestClient

from backend import cloud
from backend import match as rules
from backend.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "matches.json", tick_seconds=0.05)
    with TestClient(app) as c:
        c.data_file = tmp_path / "matches.json"
        yield c


def dashboard_match(client):
    """Create a match the way the dashboard does."""
    r = client.post("/matches", json={
        "home_team": {"id": "home", "name": "Home FC", "short_name": "HOM"},
        "away_team": {"id": "away", "name": "Away FC", "short_name": "AWY"},
        "home_lineup": [{"id": "h1", "name": "Keeper", "number": 1, "position": "GK", "is_captain": True}],
        "away_lineup": [{"id": "a9", "name": "Striker", "number": 9, "position": "ST"}],
        "venue": "Dasharath Stadium",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_health(client):
    assert client.get("/").json()["status"] == "running"


def test_create_match_dashboard_shape(client):
    match_id = dashboard_match(client)
    state = client.get(f"/matches/{match_id}/state").json()
    assert state["match"]["status"] == "created"
    assert state["home_team"]["name"] == "Home FC"
    assert state["home_lineup"][0] == {
        "player_id": "h1", "team": "home", "name": "Keeper", "short_name": None, "jersey_number": 1,
        "is_starting": True, "is_captain": True, "position_in_formation": "GK",
        "formation_x": None, "formation_y": None,
    }
    assert client.get("/matches/active").json()["id"] == match_id


def test_create_match_desktop_shape(client):
    """The payload ui/backend_sync.py sends when a match is created on the desktop."""
    r = client.post("/matches", json={
        "home_team_id": "mufc", "away_team_id": "lfc",
        "home_team": {"id": "mufc", "name": "Man Utd", "short_name": "MUN", "primary_color": "#DA291C"},
        "away_team": {"id": "lfc", "name": "Liverpool", "short_name": "LIV"},
        "home_formation": "4-3-3", "away_formation": None,
        "home_lineup": [{"player_id": "p1", "name": "A", "jersey_number": 7, "is_starting": True,
                         "is_captain": False, "position_in_formation": "RW", "team": "home"}],
        "away_lineup": [],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["id"] and body["home_formation"] == "4-3-3"
    assert client.get("/teams/mufc").json()["primary_color"] == "#DA291C"


def test_same_team_rejected(client):
    r = client.post("/matches", json={"home_team": {"id": "x", "name": "X"}, "away_team": {"id": "x", "name": "X"}})
    assert r.status_code == 400


def test_clock_runs_and_periods_advance(client):
    match_id = dashboard_match(client)
    clock = client.post(f"/matches/{match_id}/clock/start").json()
    assert clock["status"] == "running"
    assert client.get(f"/matches/{match_id}").json()["status"] == "live"

    clock = client.post(f"/matches/{match_id}/clock/set-time", json={"minutes": 44, "seconds": 59}).json()
    assert (clock["display_minute"], clock["display_second"]) == (44, 59)
    time.sleep(1.1)
    clock = client.get(f"/matches/{match_id}/clock").json()
    assert clock["display_minute"] == 45 and clock["is_added_time"]

    client.post(f"/matches/{match_id}/clock/added-time", json={"minutes": 3})
    clock = client.post(f"/matches/{match_id}/clock/next-period").json()
    assert clock["period"] == "HT" and clock["status"] == "stopped"
    assert client.get(f"/matches/{match_id}").json()["status"] == "halftime"

    clock = client.post(f"/matches/{match_id}/clock/next-period").json()
    assert (clock["period"], clock["display_minute"], clock["added_time_minutes"]) == ("2H", 45, 0)

    paused = client.post(f"/matches/{match_id}/clock/start").json()
    paused = client.post(f"/matches/{match_id}/clock/pause").json()
    time.sleep(0.3)
    assert client.get(f"/matches/{match_id}/clock").json()["display_second"] == paused["display_second"]


def test_desktop_start_at_half_time_starts_second_half(client):
    match_id = dashboard_match(client)
    client.post(f"/matches/{match_id}/clock/set-period", json={"period": "HT"})
    client.post(f"/matches/{match_id}/clock/set-time", json={"minutes": 45, "seconds": 0})
    clock = client.post(f"/matches/{match_id}/clock/start").json()
    assert (clock["period"], clock["status"]) == ("2H", "running")


def test_events_drive_score_and_undo(client):
    match_id = dashboard_match(client)
    goal = client.post(f"/matches/{match_id}/events",
                       json={"event_type": "goal", "team": "home", "player_name": "A", "player_number": 9}).json()
    client.post(f"/matches/{match_id}/events", json={"event_type": "own_goal", "team": "home", "player_name": "B"})
    client.post(f"/matches/{match_id}/events", json={"event_type": "second_yellow", "team": "away"})
    m = client.get(f"/matches/{match_id}").json()
    assert (m["home_score"], m["away_score"]) == (1, 1)
    stats = client.get(f"/matches/{match_id}/stats").json()
    assert stats["away"]["yellow_cards"] == 1 and stats["away"]["red_cards"] == 1

    assert client.delete(f"/matches/{match_id}/events/{goal['id']}").status_code == 200
    assert client.get(f"/matches/{match_id}").json()["home_score"] == 0
    assert len(client.get(f"/matches/{match_id}/events").json()) == 2
    assert len(client.get(f"/matches/{match_id}/events?include_deleted=true").json()) == 3
    assert client.delete(f"/matches/{match_id}/events/{goal['id']}").status_code == 404
    assert client.post(f"/matches/{match_id}/events", json={"event_type": "goal", "team": "left"}).status_code == 400


def test_stats_and_possession(client):
    match_id = dashboard_match(client)
    client.post(f"/matches/{match_id}/stats", json={"team": "home", "stat": "corners", "delta": 2})
    stats = client.post(f"/matches/{match_id}/stats", json={"team": "home", "stat": "corners", "delta": -5}).json()
    assert stats["home"]["corners"] == 0
    assert client.post(f"/matches/{match_id}/stats", json={"team": "home", "stat": "goals", "delta": 1}).status_code == 400

    poss = client.post(f"/matches/{match_id}/possession",
                       json={"current_team": "home", "home_pct": 55, "away_pct": 45}).json()
    assert (poss["home_pct"], poss["current_team"]) == (55, "home")
    state = client.get(f"/matches/{match_id}/state").json()
    assert state["possession"]["home_pct"] == 55


def test_possession_timer_counts_only_while_clock_runs(client):
    match_id = dashboard_match(client)
    client.post(f"/matches/{match_id}/possession/kickoff", json={"team": "away"})
    time.sleep(0.2)
    assert client.get(f"/matches/{match_id}/possession").json()["away_ms"] == 0
    client.post(f"/matches/{match_id}/clock/start")
    time.sleep(0.3)
    client.post(f"/matches/{match_id}/clock/pause")
    banked = client.get(f"/matches/{match_id}/possession").json()
    assert banked["away_ms"] >= 250 and banked["away_pct"] == 100
    time.sleep(0.2)
    assert client.get(f"/matches/{match_id}/possession").json()["away_ms"] == banked["away_ms"]


@pytest.mark.parametrize("home, away, winner", [
    ([1, 1, 1], [0, 0, 0], "home"),              # 3-0 after three each: away can't catch up
    ([1, 1, 1, 1, 1], [1, 1, 1, 1, 1], None),    # level after five
    ([1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 0], "home"),  # sudden death
    ([0, 0, 0, 0], [1, 1, 1], "away"),
])
def test_shootout_winner(home, away, winner):
    kicks = lambda xs: [{"scored": bool(x)} for x in xs]
    assert rules.shootout_winner(kicks(home), kicks(away)) == winner


def test_penalty_shootout_endpoints(client):
    match_id = dashboard_match(client)
    client.post(f"/matches/{match_id}/penalties/start", json={"first_team": "away"})
    ids = []
    for _ in range(3):
        ids.append(client.post(f"/matches/{match_id}/penalties/kick",
                               json={"team": "away", "player_name": "X", "scored": True}).json()["id"])
        client.post(f"/matches/{match_id}/penalties/kick", json={"team": "home", "player_name": "Y", "scored": False})
    shootout = client.get(f"/matches/{match_id}/penalties").json()
    assert (shootout["away_scored"], shootout["winner"], shootout["is_active"]) == (3, "away", False)
    assert client.post(f"/matches/{match_id}/penalties/kick",
                       json={"team": "home", "player_name": "Y", "scored": True}).status_code == 400

    client.delete(f"/matches/{match_id}/penalties/{ids[1]}")
    shootout = client.get(f"/matches/{match_id}/penalties").json()
    assert [k["order"] for k in shootout["away_kicks"]] == [1, 2] and shootout["winner"] is None


def test_finish_reset_delete(client):
    match_id = dashboard_match(client)
    client.post(f"/matches/{match_id}/clock/start")
    client.post(f"/matches/{match_id}/events", json={"event_type": "goal", "team": "away"})
    finished = client.post(f"/matches/{match_id}/finish").json()
    assert (finished["status"], finished["winner"], finished["current_period"]) == ("finished", "away", "FT")
    assert client.get("/matches/active").json() is None
    assert client.post(f"/matches/{match_id}/clock/start").status_code == 400

    reset = client.post(f"/matches/{match_id}/reset").json()
    assert (reset["status"], reset["away_score"], reset["id"]) == ("created", 0, match_id)
    assert client.post(f"/matches/{match_id}/end").json()["status"] == "finished"

    assert client.delete(f"/matches/{match_id}").status_code == 200
    assert client.get(f"/matches/{match_id}").status_code == 404


def test_websocket_gets_state_and_updates(client):
    match_id = dashboard_match(client)
    with client.websocket_connect(f"/ws/matches/{match_id}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state" and first["data"]["match"]["id"] == match_id
        client.post(f"/matches/{match_id}/events", json={"event_type": "goal", "team": "home"})
        update = ws.receive_json()
        assert update["type"] == "state" and update["data"]["match"]["home_score"] == 1
        client.post(f"/matches/{match_id}/clock/start")
        assert ws.receive_json()["type"] == "state"
        # The ticker pushes the running clock on its own
        tick = ws.receive_json()
        assert tick["type"] == "clock" and tick["data"]["status"] == "running"


def test_state_survives_restart(tmp_path):
    path = tmp_path / "matches.json"
    with TestClient(create_app(path)) as c:
        match_id = dashboard_match(c)
        c.post(f"/matches/{match_id}/clock/start")
        c.post(f"/matches/{match_id}/events", json={"event_type": "goal", "team": "home"})
    with TestClient(create_app(path)) as c:
        m = c.get(f"/matches/{match_id}/state").json()
        assert m["match"]["home_score"] == 1
        assert m["clock"]["status"] == "paused"


SAMPLE_FIXTURE = {
    "id": "fix-001",
    "tournament": {"id": "npl-2024", "name": "Nepal League", "logo_url": "/assets/logos/npl.png"},
    "venue": "Dasharath Stadium",
    "home_team": {"id": "dhangadhi", "name": "Dhangadhi F.C.", "short_name": "DFC",
                  "logo_url": "/assets/logos/dhangadhi.png",
                  "kits": [{"type": "home", "image_url": "/assets/kits/dhangadhi_home.png"}]},
    "away_team": {"id": "ktm", "name": "Kathmandu Rayzrs", "short_name": "KTM"},
    "home_lineup": [{"id": "d1", "name": "Keeper", "number": 1, "position": "GK"}],
    "home_substitutes": [{"id": "d12", "name": "Sub", "number": 12, "position": "GK"}],
    "away_lineup": [{"id": "k1", "name": "Keeper", "number": 1, "position": "GK"}],
    "away_substitutes": [],
}


def test_cloud_fixture_load_creates_one_match(client, monkeypatch):
    calls = []

    def fake_get(path, params=None):
        calls.append(path)
        if path == "/api/fixtures/fix-001":
            return SAMPLE_FIXTURE
        raise KeyError("not found")

    monkeypatch.setattr(cloud, "cloud_get", fake_get)
    first = client.post("/fixtures/cloud/load", json={"fixture_id": "fix-001"}).json()
    second = client.post("/fixtures/cloud/load", json={"fixture_id": "fix-001"}).json()
    assert first["success"] and first["match"]["id"] == second["match"]["id"]

    fixture = client.get("/fixtures/fix-001").json()
    assert fixture["tournament_id"] == "npl-2024"
    assert fixture["home_team"]["logo_url"].endswith("/assets/logos/dhangadhi.png")
    assert fixture["home_team"]["logo_url"].startswith("http")
    assert [p["is_starting"] for p in fixture["home_team"]["players"]] == [True, False]

    state = client.get(f"/matches/{first['match']['id']}/state").json()
    assert len(state["home_lineup"]) == 1 and state["match"]["fixture_id"] == "fix-001"
    assert client.post("/fixtures/cloud/load", json={"fixture_id": "nope"}).status_code == 404


def test_cloud_unreachable_is_502(client, monkeypatch):
    monkeypatch.setattr(cloud, "CLOUD_URL", "http://127.0.0.1:9")
    r = client.get("/fixtures/cloud/tournaments")
    assert r.status_code == 502


def test_upload_result(client, monkeypatch):
    monkeypatch.setattr(cloud, "cloud_get", lambda path, params=None: SAMPLE_FIXTURE)
    sent = {}
    monkeypatch.setattr(cloud, "cloud_post", lambda path, body: sent.update(path=path, body=body) or {"ok": True})
    match_id = client.post("/fixtures/cloud/load", json={"fixture_id": "fix-001"}).json()["match"]["id"]
    client.post(f"/matches/{match_id}/events", json={"event_type": "goal", "team": "home"})
    client.post(f"/matches/{match_id}/finish")
    assert client.post("/fixtures/upload/fix-001").json()["success"]
    assert sent["path"] == "/api/fixtures/fix-001/result"
    assert (sent["body"]["home_score"], sent["body"]["winner"]) == (1, "home")
    assert client.post("/fixtures/upload/unknown").status_code == 404


def test_load_fixtures_from_file(client, tmp_path):
    path = tmp_path / "fixtures.json"
    path.write_text('{"fixtures": [{"id": "f1", "venue": "A"}, {"id": "f2"}]}')
    assert client.post("/fixtures/load", json={"file_path": str(path)}).json()["loaded"] == 2
    assert {f["id"] for f in client.get("/fixtures").json()} == {"f1", "f2"}
    assert client.post("/fixtures/load", json={"file_path": "/etc/passwd"}).status_code == 400


def test_weather_for_venue(client, monkeypatch):
    def fake_json(url, params):
        if "geocoding" in url:
            # First lookup (full venue name) finds nothing, the city does
            if params["name"] == "Dasharath Stadium, Kathmandu":
                return {"results": []}
            return {"results": [{"latitude": 27.7, "longitude": 85.3}]}
        return {"current": {"time": "2026-11-09T12:00", "temperature_2m": 18.5, "relative_humidity_2m": 60,
                            "wind_speed_10m": 7, "wind_direction_10m": 180, "weather_code": 2, "precipitation": 0}}

    monkeypatch.setattr(cloud, "_get_json", fake_json)
    data = client.get("/weather/Dasharath Stadium, Kathmandu").json()
    assert data["coordinates"] == {"latitude": 27.7, "longitude": 85.3}
    assert data["weather"]["conditions"] == "Partly cloudy" and data["date"] == "2026-11-09"
    assert client.get("/weather/coords?latitude=27.7&longitude=85.3").status_code == 200
