"""FastAPI app: the local match API used by the match-control dashboard and
the desktop app's live sync.

Run from the repository root:

    uvicorn backend.main:app --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from . import cloud
from . import match as rules
from .store import Store

DATA_FILE = Path(os.environ.get("FSP_BACKEND_DATA", "data/backend/matches.json"))
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "FSP_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]


# ------------------------------------------------------------------ websockets


class Hub:
    """Keeps the WebSocket connections for each match and pushes updates."""

    def __init__(self) -> None:
        self.sockets: Dict[str, Set[WebSocket]] = {}

    def add(self, match_id: str, ws: WebSocket) -> None:
        self.sockets.setdefault(match_id, set()).add(ws)

    def remove(self, match_id: str, ws: WebSocket) -> None:
        self.sockets.get(match_id, set()).discard(ws)

    async def send(self, match_id: str, msg_type: str, data: Any) -> None:
        text = json.dumps({"type": msg_type, "data": data})
        for ws in list(self.sockets.get(match_id, ())):
            try:
                await ws.send_text(text)
            except Exception:
                self.remove(match_id, ws)


def create_app(data_file: Optional[Path] = DATA_FILE, tick_seconds: float = 1.0) -> FastAPI:
    store = Store(data_file)
    hub = Hub()

    async def ticker() -> None:
        # Running clocks are pushed once a second so every screen shows the
        # same time without polling.
        while True:
            await asyncio.sleep(tick_seconds)
            for match_id in list(hub.sockets):
                m = store.matches.get(match_id)
                if m and m["clock"]["status"] == "running" and hub.sockets.get(match_id):
                    await hub.send(match_id, "clock", rules.clock_view(m))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(ticker())
        try:
            yield
        finally:
            task.cancel()

    app = FastAPI(title="Football Score Pro match API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
    app.state.store = store
    app.state.hub = hub

    # ------------------------------------------------------------- helpers

    def get_match(match_id: str) -> Dict[str, Any]:
        try:
            return store.get(match_id)
        except KeyError:
            raise HTTPException(404, f"Match not found: {match_id}")

    async def mutate(match_id: str, fn, *args):
        """Apply a rule to a match, save, broadcast the new state, and return
        whatever the rule returned."""
        m = get_match(match_id)
        with store.lock:
            try:
                result = fn(m, *args)
            except rules.MatchError as exc:
                raise HTTPException(400, str(exc))
            except KeyError as exc:
                raise HTTPException(404, str(exc).strip("'"))
            store.save()
        await hub.send(match_id, "state", rules.full_state(m))
        return result

    # --------------------------------------------------------------- health

    @app.get("/")
    def health() -> Dict[str, Any]:
        return {"service": "Football Score Pro match API", "status": "running",
                "matches": len(store.matches), "fixtures_server": cloud.CLOUD_URL}

    # -------------------------------------------------------------- matches

    @app.get("/matches")
    def list_matches(status: Optional[str] = None) -> List[Dict[str, Any]]:
        return store.list(status)

    @app.get("/matches/active")
    def active_match() -> Optional[Dict[str, Any]]:
        return store.active()

    @app.post("/matches")
    def create_match(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            return store.create(payload)["match"]
        except rules.MatchError as exc:
            raise HTTPException(400, str(exc))

    @app.get("/matches/{match_id}")
    def match_summary(match_id: str) -> Dict[str, Any]:
        return get_match(match_id)["match"]

    @app.get("/matches/{match_id}/state")
    @app.get("/matches/{match_id}/snapshot")
    def match_state(match_id: str) -> Dict[str, Any]:
        return rules.full_state(get_match(match_id))

    @app.delete("/matches/{match_id}")
    def delete_match(match_id: str) -> Dict[str, Any]:
        try:
            store.delete(match_id)
        except KeyError:
            raise HTTPException(404, f"Match not found: {match_id}")
        return {"success": True}

    @app.post("/matches/{match_id}/finish")
    @app.post("/matches/{match_id}/end")
    async def finish(match_id: str) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.finish_match)
        await hub.send(match_id, "match_status", {"status": "finished", "period": "FT"})
        return m["match"]

    @app.post("/matches/{match_id}/reset")
    async def reset(match_id: str) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.reset_match)
        return m["match"]

    # ---------------------------------------------------------------- clock

    async def clock_action(match_id: str, fn, *args) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, fn, *args)
        return rules.clock_view(m)

    @app.get("/matches/{match_id}/clock")
    def get_clock(match_id: str) -> Dict[str, Any]:
        return rules.clock_view(get_match(match_id))

    @app.post("/matches/{match_id}/clock/start")
    async def clock_start(match_id: str):
        return await clock_action(match_id, rules.start_clock)

    @app.post("/matches/{match_id}/clock/pause")
    async def clock_pause(match_id: str):
        return await clock_action(match_id, rules.pause_clock)

    @app.post("/matches/{match_id}/clock/resume")
    async def clock_resume(match_id: str):
        return await clock_action(match_id, rules.resume_clock)

    @app.post("/matches/{match_id}/clock/stop")
    async def clock_stop(match_id: str):
        return await clock_action(match_id, rules.stop_clock)

    @app.post("/matches/{match_id}/clock/set-time")
    async def clock_set_time(match_id: str, body: Dict[str, Any] = Body(...)):
        return await clock_action(match_id, rules.set_clock_time,
                                  int(body.get("minutes", 0)), int(body.get("seconds", 0)))

    @app.post("/matches/{match_id}/clock/added-time")
    async def clock_added_time(match_id: str, body: Dict[str, Any] = Body(...)):
        return await clock_action(match_id, rules.set_added_time, int(body.get("minutes", 0)))

    @app.post("/matches/{match_id}/clock/next-period")
    async def clock_next_period(match_id: str):
        return await clock_action(match_id, rules.next_period)

    @app.post("/matches/{match_id}/clock/set-period")
    async def clock_set_period(match_id: str, body: Dict[str, Any] = Body(...)):
        return await clock_action(match_id, rules.set_period, str(body.get("period", "")))

    # --------------------------------------------------------------- events

    @app.get("/matches/{match_id}/events")
    def list_events(match_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        return rules.visible_events(get_match(match_id), include_deleted)

    @app.post("/matches/{match_id}/events")
    async def create_event(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        return await mutate(match_id, rules.add_event, body)

    @app.delete("/matches/{match_id}/events/{event_id}")
    async def delete_event(match_id: str, event_id: int) -> Dict[str, Any]:
        await mutate(match_id, rules.undo_event, event_id)
        return {"success": True}

    # ---------------------------------------------------------------- stats

    @app.get("/matches/{match_id}/stats")
    def get_stats(match_id: str) -> Dict[str, Any]:
        return rules.stats_by_team(get_match(match_id))

    @app.post("/matches/{match_id}/stats")
    async def post_stat(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.update_stat, body.get("team"), str(body.get("stat", "")),
                     int(body.get("delta", 1)))
        return rules.stats_by_team(m)

    # ----------------------------------------------------------- possession

    @app.get("/matches/{match_id}/possession")
    def get_possession(match_id: str) -> Dict[str, Any]:
        return rules.possession_view(get_match(match_id))

    @app.post("/matches/{match_id}/possession")
    async def post_possession(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.update_possession, body)
        return rules.possession_view(m)

    @app.post("/matches/{match_id}/possession/kickoff")
    async def post_kickoff(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.set_kickoff_team, body.get("team"))
        return rules.possession_view(m)

    # ------------------------------------------------------------ penalties

    @app.get("/matches/{match_id}/penalties")
    def get_penalties(match_id: str) -> Dict[str, Any]:
        return rules.shootout_view(get_match(match_id))

    @app.post("/matches/{match_id}/penalties/start")
    async def penalties_start(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        m = get_match(match_id)
        await mutate(match_id, rules.start_shootout, body.get("first_team", "home"))
        return rules.shootout_view(m)

    @app.post("/matches/{match_id}/penalties/kick")
    async def penalties_kick(match_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        return await mutate(match_id, rules.add_kick, body.get("team"), str(body.get("player_name") or ""),
                            bool(body.get("scored")))

    @app.delete("/matches/{match_id}/penalties/{kick_id}")
    async def penalties_undo(match_id: str, kick_id: int) -> Dict[str, Any]:
        await mutate(match_id, rules.undo_kick, kick_id)
        return {"success": True}

    # ---------------------------------------------------------------- teams

    @app.get("/teams")
    def list_teams() -> List[Dict[str, Any]]:
        return list(store.teams.values())

    @app.get("/teams/{team_id}")
    def get_team(team_id: str) -> Dict[str, Any]:
        if team_id not in store.teams:
            raise HTTPException(404, f"Team not found: {team_id}")
        return store.teams[team_id]

    @app.post("/teams")
    def create_team(team: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        if not team.get("id") or not team.get("name"):
            raise HTTPException(400, "team needs an id and a name")
        with store.lock:
            store.teams[str(team["id"])] = team
            store.save()
        return team

    # ------------------------------------------------------------- fixtures

    @app.get("/fixtures")
    def list_fixtures() -> List[Dict[str, Any]]:
        return list(store.fixtures.values())

    @app.post("/fixtures/load")
    def load_fixtures_file(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        """Load fixtures from a JSON file on this machine: either a single
        fixture or an object with a `fixtures` list."""
        path = Path(str(body.get("file_path", "")))
        if path.suffix.lower() != ".json" or not path.is_file():
            raise HTTPException(400, "file_path must point to an existing .json file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise HTTPException(400, f"could not read fixtures: {exc}")
        fixtures = data.get("fixtures", [data]) if isinstance(data, dict) else data
        loaded = [f for f in fixtures if isinstance(f, dict) and f.get("id")]
        with store.lock:
            for f in loaded:
                store.fixtures[str(f["id"])] = f
            store.save()
        return {"success": True, "loaded": len(loaded)}

    # The cloud routes come before /fixtures/{fixture_id} so they aren't
    # swallowed by it.

    async def upstream(fn, *args):
        try:
            return await run_in_threadpool(fn, *args)
        except KeyError as exc:
            raise HTTPException(404, str(exc).strip("'"))
        except cloud.UpstreamError as exc:
            raise HTTPException(502, str(exc))

    @app.get("/fixtures/cloud/tournaments")
    async def cloud_tournaments():
        return await upstream(cloud.cloud_get, "/api/tournaments")

    @app.get("/fixtures/cloud/tournaments/{tournament_id}")
    async def cloud_tournament(tournament_id: str):
        data = await upstream(cloud.cloud_get, f"/api/tournaments/{tournament_id}")
        fixtures = data.pop("fixtures", [])
        for f in fixtures:
            f.setdefault("tournament", {"id": data.get("id"), "name": data.get("name")})
        return {"tournament": data, "fixtures": fixtures}

    @app.get("/fixtures/cloud/fixtures")
    async def cloud_fixtures(tournament_id: Optional[str] = None):
        params = {"tournament_id": tournament_id} if tournament_id else None
        fixtures = await upstream(cloud.cloud_get, "/api/fixtures", params)
        # The dashboard reads fixture.tournament.name; the list only has tournament_name
        for f in fixtures:
            if not f.get("tournament") and f.get("tournament_id"):
                f["tournament"] = {"id": f["tournament_id"], "name": f.get("tournament_name")}
        return fixtures

    @app.get("/fixtures/cloud/fixtures/{fixture_id}")
    async def cloud_fixture(fixture_id: str):
        return await upstream(cloud.cloud_get, f"/api/fixtures/{fixture_id}")

    @app.get("/fixtures/cloud/teams")
    async def cloud_teams():
        return await upstream(cloud.cloud_get, "/api/teams")

    @app.post("/fixtures/cloud/load")
    async def cloud_load(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        """Copy a fixture from the fixtures server and get a match ready for it.
        Loading the same fixture again reuses the match that hasn't kicked off."""
        fixture_id = str(body.get("fixture_id") or "")
        if not fixture_id:
            raise HTTPException(400, "fixture_id is required")
        detail = await upstream(cloud.cloud_get, f"/api/fixtures/{fixture_id}")
        fixture = cloud.fixture_to_local(detail)
        with store.lock:
            store.fixtures[fixture_id] = fixture
            existing = [m for m in store.matches.values()
                        if m["match"].get("fixture_id") == fixture_id and m["match"]["status"] == "created"]
            m = existing[0] if existing else None
            if m is None:
                try:
                    m = store.create(cloud.match_payload_from_fixture(fixture))
                except rules.MatchError as exc:
                    raise HTTPException(400, str(exc))
            store.save()
        return {"success": True, "message": "Fixture loaded", "fixture": fixture, "match": m["match"]}

    @app.post("/fixtures/upload/{fixture_id}")
    async def upload_result(fixture_id: str) -> Dict[str, Any]:
        """Send the final score of the latest match for this fixture back to
        the fixtures server."""
        matches = [m for m in store.matches.values() if m["match"].get("fixture_id") == fixture_id]
        if not matches:
            raise HTTPException(404, "No match has been played for this fixture")
        m = max(matches, key=lambda x: x["match"].get("created_at") or "")
        result = {
            "match_id": m["match"]["id"],
            "status": m["match"]["status"],
            "home_score": m["match"]["home_score"],
            "away_score": m["match"]["away_score"],
            "winner": m["match"].get("winner"),
            "penalty_shootout": rules.shootout_view(m) if m["penalty_shootout"] else None,
            "events": rules.visible_events(m),
            "stats": rules.stats_row(m),
        }
        response = await upstream(cloud.cloud_post, f"/api/fixtures/{fixture_id}/result", result)
        return {"success": True, "fixture_id": fixture_id, "response": response}

    @app.get("/fixtures/{fixture_id}")
    def get_fixture(fixture_id: str) -> Dict[str, Any]:
        if fixture_id not in store.fixtures:
            raise HTTPException(404, f"Fixture not found: {fixture_id}")
        return store.fixtures[fixture_id]

    # -------------------------------------------------------------- weather

    @app.get("/weather/coords")
    async def weather_coords(latitude: float = Query(...), longitude: float = Query(...),
                             date: Optional[str] = None):
        return await upstream(cloud.weather, latitude, longitude, date, f"{latitude:.3f}, {longitude:.3f}")

    @app.get("/weather/{venue}")
    async def weather_venue(venue: str, date: Optional[str] = None):
        place = await upstream(cloud.geocode, venue)
        return await upstream(cloud.weather, place["latitude"], place["longitude"], date, venue)

    # ------------------------------------------------------------ websocket

    @app.websocket("/ws/matches/{match_id}")
    async def match_socket(ws: WebSocket, match_id: str) -> None:
        await ws.accept()
        m = store.matches.get(match_id)
        if m is None:
            await ws.close(code=4404, reason="match not found")
            return
        hub.add(match_id, ws)
        try:
            await ws.send_text(json.dumps({"type": "state", "data": rules.full_state(m)}))
            while True:
                # Clients don't need to send anything; this just notices disconnects.
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove(match_id, ws)

    return app


app = create_app()
