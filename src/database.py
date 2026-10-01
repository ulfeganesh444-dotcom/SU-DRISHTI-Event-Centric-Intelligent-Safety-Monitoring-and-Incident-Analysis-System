"""
Database module for SU-DRISHTI.
Manages the single SQLite database connection and table initialization.
Database location: Dashboard/sentinel_ai.db
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Any

# Robust project-relative path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "Dashboard" / "sentinel_ai.db"


def get_db_path() -> Path:
    """Return the resolved absolute Path to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    db_file = get_db_path()
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the SQLite database schema.
    Creates the 'events' table and performance indexes if they don't exist,
    and migrates schema gracefully.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            source TEXT NOT NULL,
            event_time TEXT NOT NULL,
            image_path TEXT NOT NULL,
            severity TEXT DEFAULT 'MEDIUM',
            status TEXT DEFAULT 'NEW',
            notes TEXT DEFAULT '',
            risk_level TEXT DEFAULT 'MEDIUM',
            event_status TEXT DEFAULT 'CONFIRMED',
            zone TEXT DEFAULT 'MONITORED',
            duration_sec REAL DEFAULT 0.0
        );
    """)

    # Migration check for existing databases
    cursor.execute("PRAGMA table_info(events);")
    cols = {row["name"] for row in cursor.fetchall()}
    if "status" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN status TEXT DEFAULT 'NEW';")
    if "notes" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN notes TEXT DEFAULT '';")
    if "risk_level" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN risk_level TEXT DEFAULT 'MEDIUM';")
    if "event_status" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN event_status TEXT DEFAULT 'CONFIRMED';")
    if "zone" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN zone TEXT DEFAULT 'MONITORED';")
    if "duration_sec" not in cols:
        cursor.execute("ALTER TABLE events ADD COLUMN duration_sec REAL DEFAULT 0.0;")
    if "end_time" not in cols:
        # Day 2: incident-formation support. NULL/'' = open or single-moment incident.
        cursor.execute("ALTER TABLE events ADD COLUMN end_time TEXT DEFAULT '';")

    # Backfill: old rows have severity but empty risk_level -> mirror it.
    # risk_level is the new canonical risk field; severity kept for compatibility.
    try:
        cursor.execute("UPDATE events SET risk_level = severity WHERE risk_level IS NULL OR risk_level = '';")
        cursor.execute("UPDATE events SET event_status = 'CONFIRMED' WHERE event_status IS NULL OR event_status = '';")
        cursor.execute("UPDATE events SET zone = 'MONITORED' WHERE zone IS NULL OR zone = '';")
    except Exception:
        pass

    # Index for fast chronological queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_event_time 
        ON events(event_time DESC);
    """)

    conn.commit()
    conn.close()


def update_event_status(event_id: int, status: str, notes: str = "") -> None:
    """Update operator response status and incident notes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE events SET status = ?, notes = ? WHERE id = ?",
        (status, notes, event_id)
    )
    conn.commit()
    conn.close()


def update_incident(event_id: int, end_time: str = "", duration_sec: float = 0.0,
                    confidence: Optional[float] = None,
                    image_path: Optional[str] = None) -> None:
    """Extend an open incident (Day 2 event grouping).

    Called when the SAME continuous event re-confirms: end_time/duration grow,
    confidence keeps the maximum, evidence stays at first confirmation.
    Only whitelisted columns are touched; never insert here.
    """
    sets = ["end_time = ?", "duration_sec = ?"]
    params: List[Any] = [str(end_time), float(duration_sec)]
    if confidence is not None:
        sets.append("confidence = ?")
        params.append(round(float(confidence), 4))
    if image_path is not None:
        sets.append("image_path = ?")
        params.append(str(image_path))
    params.append(int(event_id))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE events SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def clear_all_events() -> int:
    """Purge all event records for a fresh competition presentation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    count = cursor.fetchone()[0]
    cursor.execute("DELETE FROM events")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'events'")
    conn.commit()
    conn.close()
    return count


def fetch_all_events(limit: int = 100) -> List[sqlite3.Row]:
    """Fetch recent events ordered by event_time descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print(f"[OK] Database initialized successfully at: {get_db_path()}")
