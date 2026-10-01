"""
Unit test for PersonDetector.
Verifies model loading, inference execution, and output data structures.
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.detection.person_detection import PersonDetector, DEFAULT_MODEL_PATH

def test_person_detection():
    print(f"Testing PersonDetector loading from: {DEFAULT_MODEL_PATH}")
    assert DEFAULT_MODEL_PATH.exists(), f"Model file not found at: {DEFAULT_MODEL_PATH}"
    
    # 1. Initialize Detector
    detector = PersonDetector(model_path=DEFAULT_MODEL_PATH, conf_threshold=0.40)
    print(f"[PASS] Model loaded successfully. Total classes supported: {len(detector.class_names)}")
    assert "person" in detector.class_names.values(), "'person' class must be present in COCO classes"
    
    # 2. Test single-frame inference on synthetic frame (480, 640, 3)
    dummy_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    detections, annotated = detector.detect(dummy_frame)
    
    assert isinstance(detections, list), "Detections must be a list"
    assert annotated.shape == dummy_frame.shape, "Annotated frame must match input shape"
    print(f"[PASS] Inference ran cleanly on test frame. Detections returned: {len(detections)}")
    
    print("\n--- PERSON DETECTION MODULE TEST PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_person_detection()
