# Football Score Pro

Desktop software for running a football match broadcast: the operator sets up
the two teams, officials and on-air guests, then runs the clock, goals, cards,
substitutions and penalty shootouts from one window during the match.

I built it at FutureFrame (Lalitpur, Nepal) between 2025 and 2026, in Python
with PySide6. Around it sit a match API in FastAPI, a web match-control
dashboard in Next.js, and a sample fixtures server in Node.js.

## What's in here

| Path | What it is |
| --- | --- |
| `main.py`, `src/`, `ui/` | The desktop app (PySide6). `src/` is the domain layer: models, services and an event bus. `ui/` is the Qt interface. |
| `backend/` | FastAPI match API: matches, clock, events, stats, possession, penalty shootouts, fixtures and a WebSocket per match. The dashboard runs on it, and the desktop app pushes new matches and clock changes to it. |
| `match-control-dashboard/` | Next.js dashboard for clock, events, stats and penalty shootouts in the browser. |
| `cloud-backend/` | Express server with sample tournaments, fixtures and teams, standing in for a league's fixtures service. It also accepts final results. |
| `tests/` | Tests for the desktop services and the match API. |

```
desktop app ──┐                      ┌── fixtures server (cloud-backend, :3001)
              ├──► match API (:8000) ┤
dashboard ────┘   REST + WebSocket   └── Open-Meteo (match-day weather)
```

## The desktop app

Three tabs:

- **Match Setup**: home and away squads, formations, kits and colours (the
  kit colours are read from the jersey image), officials, commentators, hosts,
  guests and organisers. Fixtures can be loaded from a JSON file, a URL or the
  fixtures server.
- **Play On**: match clock and halves, goals with scorers and times, cards,
  and possession.
- **Subs & Penalty**: substitutions (with red-card and second-yellow locks)
  and penalty shootouts.

Keyboard shortcuts can be remapped from the Tools menu, and the operator can
lock the window with a PIN so a stray click can't change a live match.

### Structure

The UI never talks to storage directly. `main.py` builds a small service
container (team, match, tournament, officials, fixture, formation and
validation services) around a shared `EventBus`, and the UI goes through a
`BackendService` wrapper. Services publish typed events (`team_imported`,
`officials_assigned`, ...) that the UI subscribes to. Data is stored as JSON
under `data/`.

### Run it

Python 3.10 or newer.

```bash
pip install -r requirements.txt
python main.py           # the desktop app
python main.py --demo    # service demo in the terminal, no UI
pytest                   # tests
```

The operator PIN defaults to `2580`; change it from Tools > Set PIN, or set
`FSP_DEFAULT_PIN`. There is no recovery PIN unless you set `FSP_MASTER_PIN`.

## Match API

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --port 8000        # from the repository root
```

- Matches are kept in memory and written to `data/backend/matches.json` after
  every change (set `FSP_BACKEND_DATA` to move it), so a restart doesn't lose
  a live match. A clock that was running comes back paused.
- Score and card counts are worked out from the event log, so undoing an
  event always gives the right numbers.
- Every change is pushed to `ws://localhost:8000/ws/matches/{id}` as the full
  match state, and a running clock is pushed once a second.
- Fixture and weather routes call the fixtures server (`FSP_CLOUD_URL`,
  default `http://localhost:3001`) and Open-Meteo. The rest of the API works
  without them.
- Interactive docs are at `http://localhost:8000/docs`.

## Match-control dashboard

With the match API running:

```bash
cd match-control-dashboard
npm install
npm run dev              # http://localhost:3000
```

Load a fixture from the Fixtures page (needs the fixtures server), then run
the match from Match Control. Set `NEXT_PUBLIC_API_URL` if the API isn't on
`http://localhost:8000`. When the desktop app creates a match it appears on
the dashboard too; set `FSP_BACKEND_URL` for the desktop app if the API runs
elsewhere.

## Fixtures server

```bash
cd cloud-backend
npm install
npm start                # http://localhost:3001
```

`GET /api/tournaments`, `/api/fixtures`, `/api/fixtures/:id` and `/api/teams`
return the sample data in `server.js`; `POST /api/fixtures/:id/result` stores
a final result. The kit images in `assets/kits/` are plain generated shirts;
club crests are not included.

## Notes

- Sample data uses real club and player names for testing; no club artwork is
  included.
- The match API in `backend/` was rewritten after I left the project: the
  original service was never committed, so I rebuilt it against the API the
  dashboard and desktop app already call. Other later fixes (officials
  assignment, the demo, the recovery PIN, dependency updates) are in the
  commit history.
