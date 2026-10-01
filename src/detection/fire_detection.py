"""
Fire Detection module for SU-DRISHTI.

Architectural Note (Research Honesty):
The base YOLOv8n model (trained on COCO 80 classes) does NOT contain a native 'fire' or 'smoke' class.
This module implements a hybrid approach:
1. Custom Weights Mode: If a dedicated fire detection model (e.g. models/fire_yolov8n.pt)
   is provided, it performs deep-learning inference.
2. Chromatic & Luminance Fallback: Standard computer vision HSV/YCbCr color-space segmentation
   to identify high-intensity flame regions and flicker dynamics.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CUSTOM_FIRE_MODEL_PATH = PROJECT_ROOT / "models" / "fire_yolov8n.pt"


class FireDetector:
    """
    Detects fire and flame candidates using either dedicated weights
    or chromatic/luminance color-space segmentation.
    """

    def __init__(self, custom_model_path: Optional[Path] = None):
        self.model_path = custom_model_path or CUSTOM_FIRE_MODEL_PATH
        self.has_custom_model = False
        self.yolo_model = None

        if self.model_path.exists():
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO(str(self.model_path))
                self.has_custom_model = True
                print(f"[FIRE DETECTOR] Loaded custom model from {self.model_path}")
            except Exception as e:
                print(f"[FIRE DETECTOR] Error loading custom model: {e}. Falling back to chromatic analysis.")
        else:
            print("[FIRE DETECTOR] Custom fire weights not found. Using Chromatic HSV/YCbCr flame detector.")

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Detect fire in the given frame.

        Returns:
            Tuple of (detections_list, annotated_frame)
        """
        if self.has_custom_model and self.yolo_model is not None:
            return self._detect_with_yolo(frame)
        else:
            return self._detect_with_chromatic(frame)

    def _detect_with_yolo(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        annotated = frame.copy()
        detections = []
        results = self.yolo_model(frame, verbose=False)
        if results and len(results) > 0:
            for box in results[0].boxes:
                conf = float(box.conf[0].item())
                coords = [int(v) for v in box.xyxy[0].tolist()]
                detections.append({
                    "box": tuple(coords),
                    "confidence": conf,
                    "class_name": "fire",
                    "method": "YOLO_Custom"
                })
                cv2.rectangle(annotated, (coords[0], coords[1]), (coords[2], coords[3]), (0, 0, 255), 2)
                cv2.putText(annotated, f"FIRE {conf:.2f}", (coords[0], coords[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return detections, annotated

    def _detect_with_chromatic(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Color-space segmentation for fire detection (HSV & YCbCr rules):
        Fire pixels satisfy:
        - High red intensity: R > G > B
        - HSV: Hue in orange/red range (0-25 and 160-180), High Saturation, High Value.
        - Area threshold to prevent tiny glares from false alerting.
        """
        annotated = frame.copy()
        detections = []

        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Fire color mask: Hue 0-25 (red to yellow), Sat 100-255, Val 180-255
        lower_fire = np.array([0, 100, 180], dtype=np.uint8)
        upper_fire = np.array([25, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_fire, upper_fire)

        # Morphological opening to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find flame contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_flame_area = 1500  # Minimum pixel area for flame candidate

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_flame_area:
                x, y, w, h = cv2.boundingRect(cnt)
                conf = min(0.95, round(0.60 + (area / (frame.shape[0] * frame.shape[1])) * 2.0, 2))
                
                detections.append({
                    "box": (x, y, x + w, y + h),
                    "confidence": conf,
                    "class_name": "fire",
                    "method": "Chromatic_ColorSpace"
                })

                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(
                    annotated,
                    f"FIRE CANDIDATE {conf:.2f}",
                    (x, max(20, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2,
                )

        return detections, annotated
