# Football Score Pro

Desktop software for running a football match broadcast: the operator sets up
the two teams, officials and on-air guests, then runs the clock, goals, cards,
substitutions and penalty shootouts from one window during the match.

I built it at FutureFrame (Lalitpur, Nepal) between 2025 and 2026, in Python
with PySide6. The repository also holds two smaller pieces that grew around
it: a sample fixtures server in Node.js and a web match-control dashboard in
Next.js.

## What's in here

| Path | What it is |
| --- | --- |
| `main.py`, `src/`, `ui/` | The desktop app (PySide6). `src/` is the domain layer: models, services and an event bus. `ui/` is the Qt interface. |
| `cloud-backend/` | Express server with sample tournaments, fixtures and teams. The desktop app's fixture loader can pull a match from it. |
| `match-control-dashboard/` | Next.js dashboard for clock, events, stats and penalty shootouts in the browser. |
| `tests/` | Service-level tests that run without the UI. |

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

## Fixtures server

```bash
cd cloud-backend
npm install
npm start                # http://localhost:3001
```

`GET /api/tournaments`, `/api/fixtures`, `/api/fixtures/:id` and `/api/teams`
return the sample data in `server.js`. The kit images in `assets/kits/` are
plain generated shirts; club crests are not included.

## Match-control dashboard

```bash
cd match-control-dashboard
npm install
npm run dev              # http://localhost:3000
```

The dashboard and the desktop app's live sync (`ui/backend_api.py`,
`ui/backend_ws_client.py`) expect a match API at `http://localhost:8000`
(set `NEXT_PUBLIC_API_URL` to change it). That API was a separate FastAPI
service and is **not in this repository**, so without it the dashboard loads
but can't create or update matches. The desktop app works on its own.

## Notes

- Sample data uses real club and player names for testing; no club artwork is
  included.
- This is the code as it stood when I left the project, with a few fixes
  applied afterwards (officials assignment, the demo, the recovery PIN, and
  dependency updates in the dashboard). See the commit history.
