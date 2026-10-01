"""
Unit test for src/database.py.
Verifies table creation, schema integrity, and query execution.
"""
import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, get_connection, get_db_path, fetch_all_events

def test_database():
    print(f"Testing database initialization at: {get_db_path()}")
    init_db()
    
    assert get_db_path().exists(), "Database file does not exist!"
    print("[PASS] Database file exists.")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check table columns
    cursor.execute("PRAGMA table_info(events);")
    columns = {row["name"]: row["type"] for row in cursor.fetchall()}
    print(f"Columns in 'events' table: {columns}")
    
    required_cols = ["id", "object_name", "confidence", "source", "event_time", "image_path"]
    for col in required_cols:
        assert col in columns, f"Missing required column: {col}"
    print("[PASS] All required columns exist.")
    
    # Insert a test record
    cursor.execute("""
        INSERT INTO events (object_name, confidence, source, event_time, image_path, severity)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test_person", 0.95, "Webcam", "2026-09-24 12:00:00", "screenshots/test.jpg", "MEDIUM"))
    conn.commit()
    
    # Verify retrieval
    events = fetch_all_events(limit=5)
    assert len(events) > 0, "No events returned from fetch_all_events"
    latest = events[0]
    print(f"[PASS] Retrieved event: ID={latest['id']}, Object={latest['object_name']}, Conf={latest['confidence']}")
    
    # Clean up test row
    cursor.execute("DELETE FROM events WHERE object_name = 'test_person'")
    conn.commit()
    conn.close()
    
    print("\n--- DATABASE MODULE TEST PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_database()
