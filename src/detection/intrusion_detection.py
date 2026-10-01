"""
Intrusion Detection module for SU-DRISHTI.
Implements virtual perimeter / Region-of-Interest (ROI) polygon tripwires.
Detects unauthorized access when human targets enter defined restricted boundaries.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np


class IntrusionDetector:
    """
    Monitors a configurable Region of Interest (ROI) polygon tripwire
    and detects intrusions based on human target spatial intersection.
    """

    def __init__(self, zone_points_normalized: Optional[List[Tuple[float, float]]] = None):
        """
        Args:
            zone_points_normalized: List of (x_norm, y_norm) coordinates from 0.0 to 1.0.
                                    Defaults to a rectangular zone in the right half of the frame.
        """
        if zone_points_normalized is None:
            # Default zone: Right quadrant (e.g. door/entryway simulation)
            self.zone_norm = [
                (0.50, 0.20),
                (0.95, 0.20),
                (0.95, 0.90),
                (0.50, 0.90),
            ]
        else:
            self.zone_norm = zone_points_normalized

    def get_pixel_polygon(self, frame_w: int, frame_h: int) -> np.ndarray:
        """Convert normalized coordinates to integer pixel polygon."""
        points = [(int(x * frame_w), int(y * frame_h)) for x, y in self.zone_norm]
        return np.array(points, dtype=np.int32)

    def check_intrusion(
        self,
        box: Tuple[int, int, int, int],
        frame_w: int,
        frame_h: int
    ) -> bool:
        """
        Check if a bounding box intersects the restricted zone polygon.
        Uses the bottom-center point (feet position) of the human target.

        Args:
            box: (x1, y1, x2, y2)
            frame_w: Frame width
            frame_h: Frame height

        Returns:
            bool: True if inside restricted zone.
        """
        x1, y1, x2, y2 = box
        # Test the bottom-center (footprint) of the person
        foot_x = (x1 + x2) / 2.0
        foot_y = float(y2)

        poly = self.get_pixel_polygon(frame_w, frame_h)
        # cv2.pointPolygonTest returns >= 0 if point is inside or on edge
        res = cv2.pointPolygonTest(poly, (foot_x, foot_y), False)
        return res >= 0

    def draw_zone(self, frame: np.ndarray, is_breached: bool) -> np.ndarray:
        """Draw the restricted boundary on the frame with visual status alert."""
        h, w = frame.shape[:2]
        poly = self.get_pixel_polygon(w, h)

        # Color: Red if breached, Amber/Cyan if armed
        color = (0, 0, 255) if is_breached else (0, 215, 255)
        status_label = "RESTRICTED ZONE [BREACH DETECTED]" if is_breached else "RESTRICTED ZONE [SECURE]"

        # Semi-transparent polygon fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [poly], color)
        alpha = 0.25 if is_breached else 0.15
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

        # Border
        cv2.polylines(frame, [poly], isClosed=True, color=color, thickness=2)

        # Banner at first vertex
        x0, y0 = poly[0]
        cv2.putText(
            frame,
            status_label,
            (x0, max(25, y0 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )
        return frame
