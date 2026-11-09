"""Match storage: an in-memory dict, written to a JSON file after every change
so a live match survives a backend restart."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import match as rules


class Store:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else None
        self.lock = threading.RLock()
        self.matches: Dict[str, Dict[str, Any]] = {}
        self.fixtures: Dict[str, Dict[str, Any]] = {}
        self.teams: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------ persistence

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.matches = data.get("matches", {})
        self.fixtures = data.get("fixtures", {})
        self.teams = data.get("teams", {})
        # A clock that was running when the process stopped can't be trusted
        # to have kept time, so it comes back paused at the last saved value.
        for m in self.matches.values():
            if m["clock"]["status"] == "running":
                m["clock"]["running_since"] = None
                m["clock"]["status"] = "paused"
                m["possession"]["since"] = None

    def save(self) -> None:
        if not self.path:
            return
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(
                {"matches": self.matches, "fixtures": self.fixtures, "teams": self.teams},
                ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)

    # ---------------------------------------------------------------- matches

    def get(self, match_id: str) -> Dict[str, Any]:
        m = self.matches.get(match_id)
        if m is None:
            raise KeyError(f"match {match_id} not found")
        return m

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        m = rules.new_match(payload)
        with self.lock:
            self.matches[m["match"]["id"]] = m
            for side in ("home_team", "away_team"):
                team = m[side]
                self.teams.setdefault(team["id"], dict(team))
            self.save()
        return m

    def delete(self, match_id: str) -> None:
        with self.lock:
            self.get(match_id)
            del self.matches[match_id]
            self.save()

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        items = [m["match"] for m in self.matches.values()]
        if status:
            items = [x for x in items if x["status"] == status]
        return sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)

    def active(self) -> Optional[Dict[str, Any]]:
        """The match the dashboard should show: the latest live or half-time
        match, otherwise the latest one that hasn't kicked off."""
        for statuses in (("live", "halftime"), ("created",)):
            candidates = [x for x in self.list() if x["status"] in statuses]
            if candidates:
                return candidates[0]
        return None
