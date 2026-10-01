"""
Event Logger module for SU-DRISHTI.
Responsible for inserting incident records into the SQLite database.
Database: Dashboard/sentinel_ai.db
"""

from datetime import datetime
from typing import Optional
from src.database import get_connection, init_db


def save_event(
    object_name: str,
    confidence: float,
    source: str,
    event_time: Optional[str] = None,
    image_path: str = "",
    severity: str = "MEDIUM",
    risk_level: Optional[str] = None,
    event_status: str = "CONFIRMED",
    zone: str = "MONITORED",
    duration_sec: float = 0.0,
    end_time: str = "",
) -> int:
    """
    Save a detected event into the SQLite database.

    Args:
        object_name: Label of detected object or event (e.g. 'person', 'fall', 'fire').
        confidence: Model prediction confidence score (0.0 to 1.0).
        source: Input stream identifier (e.g. 'Webcam', 'video.mp4').
        event_time: Timestamp string (YYYY-MM-DD HH:MM:SS). Defaults to current time if None.
        image_path: Relative path to saved evidence screenshot (e.g. 'screenshots/...jpg').
        severity: Legacy alert tier (kept for compatibility; mirrors risk_level).
        risk_level: Canonical risk tier ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
        event_status: Verification state ('SUSPECTED', 'VERIFYING', 'CONFIRMED').
        zone: Context zone ('MONITORED' or 'RESTRICTED').
        duration_sec: Persistence duration in seconds before confirmation.

    Returns:
        int: The auto-generated database ID of the inserted event.
    """
    if event_time is None:
        event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # risk_level is canonical; severity mirrors it for backward compatibility.
    if risk_level is None:
        risk_level = severity
    else:
        severity = risk_level

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (object_name, confidence, source, event_time, image_path,
                            severity, risk_level, event_status, zone, duration_sec, end_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (object_name, round(float(confidence), 4), str(source), str(event_time),
          str(image_path), str(severity), str(risk_level),
          str(event_status), str(zone), float(duration_sec), str(end_time)))

    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(
        f"[EVENT LOGGED] ID: {event_id} | Object: {object_name} ({confidence:.2f}) | "
        f"Source: {source} | Risk: {risk_level} | Status: {event_status} | "
        f"Zone: {zone} | Duration: {duration_sec:.1f}s | Time: {event_time} | Evidence: {image_path}"
    )

    return event_id
