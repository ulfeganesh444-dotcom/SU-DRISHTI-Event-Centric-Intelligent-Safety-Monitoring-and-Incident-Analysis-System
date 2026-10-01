"""
Unit tests for EventFilter.
Verifies whitelisting, confidence gates, and the smart cooldown debounce mechanism.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.event_filter import EventFilter

def test_event_filter():
    print("Testing EventFilter module...")
    
    # Initialize filter with a short cooldown of 0.5s for fast unit testing
    filter_obj = EventFilter(
        important_objects={"person", "fire", "car"},
        min_confidence=0.60,
        default_cooldown=0.5,
        critical_cooldown=0.3
    )
    
    # 1. Non-whitelisted object should be rejected
    assert not filter_obj.should_log("chair", 0.95), "Non-whitelisted object should not pass"
    print("[PASS] Non-whitelisted object correctly rejected.")
    
    # 2. Low confidence should be rejected
    assert not filter_obj.should_log("person", 0.45), "Low confidence should not pass"
    print("[PASS] Low confidence object correctly rejected.")
    
    # 3. High confidence whitelisted object should pass
    first_logged = filter_obj.should_log("person", 0.92)
    assert first_logged, "First valid detection should pass"
    print("[PASS] First valid detection passed.")
    
    # 4. Immediate second detection should be blocked by Cooldown
    immediate_second = filter_obj.should_log("person", 0.94)
    assert not immediate_second, "Detection within cooldown period should be debounced"
    print("[PASS] Duplicate detection correctly blocked by Cooldown mechanism.")
    
    # 5. Wait for cooldown to expire
    time.sleep(0.55)
    after_cooldown = filter_obj.should_log("person", 0.91)
    assert after_cooldown, "Detection after cooldown should pass"
    print("[PASS] Detection after cooldown passed successfully.")
    
    print("\n--- EVENT FILTER TEST PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_event_filter()
