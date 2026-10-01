"""
Unit tests for SU-DRISHTI Safety Detection Modules:
- Fall Detection (Aspect-Ratio Kinematics)
- Intrusion Detection (Polygon ROI Tripwire)
- Fire Detection (Chromatic Segmentation)
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.detection.fall_detection import FallDetector
from src.detection.intrusion_detection import IntrusionDetector
from src.detection.fire_detection import FireDetector

def test_fall_detector():
    print("\n--- Testing FallDetector ---")
    detector = FallDetector(persistence_frames=3)
    frame_h = 480
    
    # Standing person: width=80, height=300 (H/W = 3.75)
    standing_box = (100, 50, 180, 350)
    for _ in range(5):
        res = detector.evaluate_person(standing_box, 0.90, frame_h)
    assert not res["is_fall"], "Standing person should NOT trigger fall"
    print(f"[PASS] Standing posture correctly identified as normal (H/W = {res['aspect_ratio']}).")
    
    # Fallen person: width=300, height=70 (H/W = 0.23, horizontal near ground)
    fallen_box = (100, 380, 400, 450)
    for i in range(3):
        res = detector.evaluate_person(fallen_box, 0.90, frame_h)
    assert res["is_fall"], "Persistent horizontal posture should trigger fall alert"
    print(f"[PASS] Fall correctly detected: {res['reason']}.")


def test_intrusion_detector():
    print("\n--- Testing IntrusionDetector ---")
    # Zone covers right half of 640x480 frame: x from 0.5 to 0.95, y from 0.2 to 0.9
    detector = IntrusionDetector()
    frame_w, frame_h = 640, 480
    
    # Target 1: Left safe zone (x = 100 to 180, feet at y = 300)
    safe_box = (100, 100, 180, 300)
    is_breach = detector.check_intrusion(safe_box, frame_w, frame_h)
    assert not is_breach, "Target in safe zone should NOT trigger intrusion"
    print("[PASS] Target in authorized zone correctly identified as safe.")
    
    # Target 2: Inside restricted zone (x = 400 to 480, feet at y = 350)
    breach_box = (400, 100, 480, 350)
    is_breach = detector.check_intrusion(breach_box, frame_w, frame_h)
    assert is_breach, "Target inside restricted polygon MUST trigger intrusion"
    print("[PASS] Target inside restricted zone correctly detected as intrusion breach.")


def test_fire_detector():
    print("\n--- Testing FireDetector ---")
    detector = FireDetector()
    
    # Blank gray frame (no fire)
    blank_frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    dets, _ = detector.detect(blank_frame)
    assert len(dets) == 0, "No fire should be detected in gray frame"
    print("[PASS] Normal frame contains 0 false fire alerts.")
    
    # Synthetic fire block (bright orange/red)
    fire_frame = blank_frame.copy()
    # OpenCV BGR: Blue=20, Green=120, Red=255
    fire_frame[200:300, 200:300] = (20, 120, 255)
    dets, _ = detector.detect(fire_frame)
    assert len(dets) > 0, "Bright fire color candidate should be detected"
    print(f"[PASS] Fire candidate detected with confidence: {dets[0]['confidence']}.")


if __name__ == "__main__":
    test_fall_detector()
    test_intrusion_detector()
    test_fire_detector()
    print("\n==================================================")
    print("ALL SAFETY DETECTION MODULE TESTS PASSED")
    print("==================================================")
