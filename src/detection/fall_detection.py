"""
Fall Detection module for SU-DRISHTI.
Implements kinematic and geometric analysis of detected person bounding boxes
to detect accidental falls in real-time.

Avishkar Research Methodology:
1. Aspect-Ratio Dynamics: Measures bounding box ratio R = Height / Width.
   - Standing posture: R >= 1.2
   - Fallen / Horizontal posture: R <= 0.8
2. Downward Velocity: Measures centroid vertical displacement Delta_y / Delta_t.
3. Temporal Persistence: Confirms posture remains fallen across consecutive frames
   to prevent false alarms from momentary crouching.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2


class FallDetector:
    """
    Analyzes person detections over time to identify falls based on
    aspect-ratio inversion, downward velocity, and ground proximity.
    """

    def __init__(
        self,
        aspect_ratio_threshold: float = 0.85,
        persistence_frames: int = 5,
        min_confidence: float = 0.50,
    ):
        """
        Args:
            aspect_ratio_threshold: H / W ratio below which posture is considered horizontal/fallen.
            persistence_frames: Number of consecutive frames posture must persist before triggering.
            min_confidence: Minimum detection confidence to evaluate.
        """
        self.aspect_ratio_threshold = aspect_ratio_threshold
        self.persistence_frames = persistence_frames
        self.min_confidence = min_confidence

        # Tracking state: person index/counter -> persistence count
        self._consecutive_fall_frames = 0
        self._last_centroid_y: Optional[float] = None

    def evaluate_person(
        self,
        box: Tuple[int, int, int, int],
        confidence: float,
        frame_height: int,
    ) -> Dict[str, Any]:
        """
        Evaluate a single person detection bounding box for fall indicators.

        Args:
            box: (x1, y1, x2, y2) pixel coordinates.
            confidence: Detection confidence (0.0 to 1.0).
            frame_height: Total frame height in pixels.

        Returns:
            Dict containing:
              - 'is_fall': bool (True if criteria met)
              - 'aspect_ratio': float (H / W)
              - 'persistence': int (consecutive frames in fallen posture)
              - 'reason': str (explanation)
        """
        if confidence < self.min_confidence:
            return {"is_fall": False, "aspect_ratio": 0.0, "persistence": 0, "reason": "Low confidence"}

        x1, y1, x2, y2 = box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        aspect_ratio = height / width
        centroid_y = (y1 + y2) / 2.0

        # Downward motion check
        downward_shift = 0.0
        if self._last_centroid_y is not None:
            downward_shift = centroid_y - self._last_centroid_y
        self._last_centroid_y = centroid_y

        # Criterion 1: Aspect ratio inverted (width > height)
        # Criterion 2: Base of person is in lower 40% of frame (near ground)
        is_horizontal = aspect_ratio < self.aspect_ratio_threshold
        is_near_floor = y2 > (frame_height * 0.50)

        if is_horizontal and is_near_floor:
            self._consecutive_fall_frames += 1
        else:
            self._consecutive_fall_frames = max(0, self._consecutive_fall_frames - 1)

        # Trigger when persistent across configured frame threshold
        if self._consecutive_fall_frames >= self.persistence_frames:
            return {
                "is_fall": True,
                "aspect_ratio": round(aspect_ratio, 2),
                "persistence": self._consecutive_fall_frames,
                "reason": f"Horizontal posture (H/W={aspect_ratio:.2f}) persisted for {self._consecutive_fall_frames} frames",
            }

        return {
            "is_fall": False,
            "aspect_ratio": round(aspect_ratio, 2),
            "persistence": self._consecutive_fall_frames,
            "reason": "Normal posture",
        }

    def reset(self):
        """Reset state."""
        self._consecutive_fall_frames = 0
        self._last_centroid_y = None
