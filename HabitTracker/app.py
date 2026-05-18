"""Daily habit tracker — Flask + SQLite."""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "habits.db"

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS habits (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              archived INTEGER NOT NULL DEFAULT 0
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_habits_active_name
            ON habits(name) WHERE archived = 0;

            CREATE TABLE IF NOT EXISTS daily_entries (
              habit_id INTEGER NOT NULL,
              entry_date TEXT NOT NULL,
              completed INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (habit_id, entry_date),
              FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS day_meta (
              entry_date TEXT PRIMARY KEY,
              hours_worked REAL,
              wake_time TEXT,
              bed_time TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _active_habit_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM habits WHERE archived = 0 ORDER BY id ASC"
    ).fetchall()
    return [int(r["id"]) for r in rows]


def _active_habits(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name FROM habits WHERE archived = 0 ORDER BY id ASC"
    ).fetchall()
    return [{"id": int(r["id"]), "name": r["name"]} for r in rows]


def _day_complete(conn: sqlite3.Connection, d: date) -> bool:
    habit_ids = _active_habit_ids(conn)
    if not habit_ids:
        return False
    ds = d.isoformat()
    placeholders = ",".join("?" * len(habit_ids))
    rows = conn.execute(
        f"""
        SELECT habit_id, completed
        FROM daily_entries
        WHERE entry_date = ? AND habit_id IN ({placeholders})
        """,
        (ds, *habit_ids),
    ).fetchall()
    by_habit = {int(r["habit_id"]): int(r["completed"]) for r in rows}
    for hid in habit_ids:
        if by_habit.get(hid, 0) != 1:
            return False
    return True


def _all_complete_dates(conn: sqlite3.Connection) -> set[date]:
    habit_ids = _active_habit_ids(conn)
    if not habit_ids:
        return set()
    # Dates that appear in daily_entries for active habits
    rows = conn.execute(
        """
        SELECT DISTINCT entry_date
        FROM daily_entries
        WHERE habit_id IN (SELECT id FROM habits WHERE archived = 0)
        """
    ).fetchall()
    candidates: set[date] = set()
    for r in rows:
        try:
            candidates.add(date.fromisoformat(r["entry_date"]))
        except ValueError:
            continue
    return {d for d in candidates if _day_complete(conn, d)}


def compute_habit_streaks(conn: sqlite3.Connection) -> dict[int, int]:
    """Return {habit_id: current_streak_days} for every active habit."""
    today = date.today()
    rows = conn.execute(
        """
        SELECT habit_id, entry_date
        FROM daily_entries
        WHERE habit_id IN (SELECT id FROM habits WHERE archived = 0)
          AND completed = 1
        ORDER BY habit_id, entry_date DESC
        """
    ).fetchall()

    habit_dates: dict[int, set] = defaultdict(set)
    for r in rows:
        try:
            habit_dates[int(r["habit_id"])].add(date.fromisoformat(r["entry_date"]))
        except ValueError:
            continue

    result: dict[int, int] = {}
    for hid in _active_habit_ids(conn):
        complete = habit_dates.get(hid, set())
        anchor = today if today in complete else today - timedelta(days=1)
        streak = 0
        d = anchor
        while d in complete:
            streak += 1
            d -= timedelta(days=1)
        result[hid] = streak
    return result


def compute_streaks(conn: sqlite3.Connection) -> tuple[int, int]:
    complete = _all_complete_dates(conn)
    today = date.today()

    # Current streak: from today if complete, else from yesterday
    if today in complete:
        anchor = today
    else:
        anchor = today - timedelta(days=1)

    current = 0
    d = anchor
    while d in complete:
        current += 1
        d -= timedelta(days=1)

    # Longest streak over all complete dates (consecutive calendar days)
    if not complete:
        return current, 0
    sorted_days = sorted(complete)
    longest = 1
    run = 1
    for i in range(1, len(sorted_days)):
        if sorted_days[i] - sorted_days[i - 1] == timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, run)
    return current, longest


def _day_payload(conn: sqlite3.Connection, d: date) -> dict:
    ds = d.isoformat()
    habit_ids = _active_habit_ids(conn)
    meta_row = conn.execute(
        "SELECT hours_worked, wake_time, bed_time FROM day_meta WHERE entry_date = ?",
        (ds,),
    ).fetchone()

    meta = {
        "hours_worked": None,
        "wake_time": None,
        "bed_time": None,
    }
    if meta_row:
        hw = meta_row["hours_worked"]
        meta["hours_worked"] = float(hw) if hw is not None else None
        meta["wake_time"] = meta_row["wake_time"]
        meta["bed_time"] = meta_row["bed_time"]

    completions: dict[str, int] = {}
    if habit_ids:
        ph = ",".join("?" * len(habit_ids))
        rows = conn.execute(
            f"""
            SELECT habit_id, completed FROM daily_entries
            WHERE entry_date = ? AND habit_id IN ({ph})
            """,
            (ds, *habit_ids),
        ).fetchall()
        for r in rows:
            completions[str(int(r["habit_id"]))] = int(r["completed"])

    return {
        "date": ds,
        "meta": meta,
        "completions": completions,
        "complete": _day_complete(conn, d),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    conn = get_db()
    try:
        offset = max(0, int(request.args.get("offset", 0)))
        limit = min(100, max(1, int(request.args.get("limit", 11))))
    except ValueError:
        offset, limit = 0, 11

    today = date.today()
    days: list[dict] = []
    for i in range(offset, offset + limit):
        d = today - timedelta(days=i)
        days.append(_day_payload(conn, d))

    current, longest = compute_streaks(conn)
    habit_streaks = compute_habit_streaks(conn)
    has_more = True

    return jsonify(
        {
            "habits": _active_habits(conn),
            "days": days,
            "stats": {"current_streak": current, "longest_streak": longest},
            "habit_streaks": {str(k): v for k, v in habit_streaks.items()},
            "has_more": has_more,
            "today": today.isoformat(),
        }
    )


@app.route("/api/habits", methods=["POST"])
def api_habits_create():
    conn = get_db()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if len(name) > 200:
        return jsonify({"error": "name too long"}), 400
    created = datetime.now().isoformat()
    try:
        cur = conn.execute(
            "INSERT INTO habits (name, created_at, archived) VALUES (?, ?, 0)",
            (name, created),
        )
        conn.commit()
        hid = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "habit name already exists"}), 409

    current, longest = compute_streaks(conn)
    return jsonify(
        {
            "habit": {"id": hid, "name": name},
            "stats": {"current_streak": current, "longest_streak": longest},
        }
    )


@app.route("/api/habits/<int:habit_id>", methods=["DELETE"])
def api_habits_archive(habit_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM habits WHERE id = ? AND archived = 0", (habit_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    conn.execute("UPDATE habits SET archived = 1 WHERE id = ?", (habit_id,))
    conn.commit()
    current, longest = compute_streaks(conn)
    return jsonify({"ok": True, "stats": {"current_streak": current, "longest_streak": longest}})


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    conn = get_db()
    data = request.get_json(silent=True) or {}
    try:
        habit_id = int(data["habit_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "habit_id required"}), 400
    entry_date_str = str(data.get("date", "")).strip()
    try:
        entry_date = date.fromisoformat(entry_date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    completed = bool(data.get("completed", False))

    row = conn.execute(
        "SELECT id FROM habits WHERE id = ? AND archived = 0", (habit_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "habit not found"}), 404

    ds = entry_date.isoformat()
    conn.execute(
        """
        INSERT INTO daily_entries (habit_id, entry_date, completed)
        VALUES (?, ?, ?)
        ON CONFLICT(habit_id, entry_date) DO UPDATE SET completed = excluded.completed
        """,
        (habit_id, ds, 1 if completed else 0),
    )
    conn.commit()

    day_complete = _day_complete(conn, entry_date)
    current, longest = compute_streaks(conn)
    habit_streaks = compute_habit_streaks(conn)
    return jsonify(
        {
            "ok": True,
            "date": ds,
            "day_complete": day_complete,
            "stats": {"current_streak": current, "longest_streak": longest},
            "habit_streaks": {str(k): v for k, v in habit_streaks.items()},
        }
    )


@app.route("/api/meta", methods=["POST"])
def api_meta():
    conn = get_db()
    data = request.get_json(silent=True) or {}
    entry_date_str = str(data.get("date", "")).strip()
    try:
        entry_date = date.fromisoformat(entry_date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    ds = entry_date.isoformat()

    hours_raw = data.get("hours_worked")
    hours_worked: float | None
    if hours_raw is None or hours_raw == "":
        hours_worked = None
    else:
        try:
            hours_worked = float(hours_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid hours_worked"}), 400

    def norm_time(key: str) -> str | None:
        v = data.get(key)
        if v is None or str(v).strip() == "":
            return None
        s = str(v).strip()
        # Accept HTML time input "HH:MM" or "HH:MM:SS"
        parts = s.split(":")
        if len(parts) < 2:
            return None
        try:
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                return None
            return f"{h:02d}:{m:02d}"
        except ValueError:
            return None

    wake_time = norm_time("wake_time")
    bed_time = norm_time("bed_time")

    conn.execute(
        """
        INSERT INTO day_meta (entry_date, hours_worked, wake_time, bed_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(entry_date) DO UPDATE SET
          hours_worked = excluded.hours_worked,
          wake_time = excluded.wake_time,
          bed_time = excluded.bed_time
        """,
        (ds, hours_worked, wake_time, bed_time),
    )
    conn.commit()
    current, longest = compute_streaks(conn)
    return jsonify({"ok": True, "stats": {"current_streak": current, "longest_streak": longest}})


init_db()


if __name__ == "__main__":
    # macOS often binds AirPlay Receiver to port 5000 (empty 403 from AirTunes).
    port = int(os.environ.get("HABITTRACKER_PORT", os.environ.get("PORT", "5001")))
    print(f"Habit Tracker: http://127.0.0.1:{port}/", flush=True)
    app.run(host="127.0.0.1", port=port, debug=True)
