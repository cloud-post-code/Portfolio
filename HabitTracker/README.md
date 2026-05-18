# Daily Habit Tracker

Local Flask + SQLite habit tracker: check off habits by day, log wake/bed/hours, streaks, and confetti when today is fully complete.

## Setup

```bash
cd HabitTracker
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Or one step from this folder: `./run.sh` (after `chmod +x run.sh` once).

**You must leave that terminal running.** If you close it or press Ctrl+C, the site stops and the browser shows `ERR_CONNECTION_REFUSED`.

When the server starts you should see:

`Habit Tracker: http://127.0.0.1:5001/`

Open that URL (default port is **5001** — macOS often uses **5000** for AirPlay Receiver).

### `ERR_CONNECTION_REFUSED`

1. Start the app from the `HabitTracker` folder: `python3 app.py` (see lines above).
2. Use **port 5001**: `http://127.0.0.1:5001/` — not `5000` unless you changed it.
3. If you see import errors, run `python3 -m pip install -r requirements.txt` again inside the venv.

Override the port: `HABITTRACKER_PORT=8080 python3 app.py` then open `http://127.0.0.1:8080/`.

Data is stored in `habits.db` in this folder (created on first run).
