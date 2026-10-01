"""
Test for screenshot capture and event logger persistence.
Verifies the complete bridge: Frame -> Screenshot File -> Database Record.
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, get_connection
from src.alerts.screenshot import capture_screenshot
from src.event_logger import save_event

def test_screenshot_and_logger():
    print("Testing screenshot capture and event logging...")
    init_db()
    
    # 1. Create a mock frame (640x480 synthetic frame)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (50, 120, 200) # Orange-ish background
    
    # 2. Capture screenshot
    relative_path = capture_screenshot(frame, object_name="test_alert")
    full_path = PROJECT_ROOT / relative_path
    
    print(f"[PASS] Screenshot saved: {relative_path}")
    assert full_path.exists(), f"Screenshot file not found at {full_path}"
    assert full_path.stat().st_size > 0, "Screenshot file is empty"
    
    # 3. Log event into SQLite
    event_id = save_event(
        object_name="test_alert",
        confidence=0.965,
        source="Webcam_Test",
        image_path=relative_path,
        severity="MEDIUM"
    )
    assert event_id is not None and event_id > 0, "Invalid event ID returned"
    
    # 4. Verify in Database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    
    assert row is not None, "Failed to retrieve logged event from DB"
    assert row["object_name"] == "test_alert"
    assert abs(row["confidence"] - 0.965) < 0.001
    assert row["image_path"] == relative_path
    print(f"[PASS] Database verification: Row {row['id']} matches saved screenshot {row['image_path']}")
    
    # Cleanup test artifacts
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    if full_path.exists():
        full_path.unlink()
        
    print("\n--- SCREENSHOT & EVENT LOGGER TEST PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_screenshot_and_logger()
