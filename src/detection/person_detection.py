"""
High-Precision Tactical Target Tracking & Object Detection for SU-DRISHTI.
Implements ByteTrack multi-object tracking, target trajectory trails, dwell timing,
kinematic telemetry, tactical corner reticles, and ethical privacy redaction.
"""

from collections import deque
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import time
import cv2
import numpy as np
from ultralytics import YOLO

# Project-relative path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "yolov8n.pt"


class TacticalDetector:
    """
    Military/Enterprise grade detector and tracker.
    Provides persistent Target IDs, breadcrumb motion trajectories,
    kinematic aspect-ratio telemetry, and ethical privacy redaction.
    """

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        conf_threshold: float = 0.50,
        track_history_length: int = 25,
    ):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model weights not found at: {self.model_path}")

        # Load YOLO model
        self.model = YOLO(str(self.model_path))
        self.conf_threshold = conf_threshold
        self.class_names = self.model.names

        # Tracking state
        self.track_history_len = track_history_length
        self.trajectories: Dict[int, deque] = {}
        self.track_start_times: Dict[int, float] = {}
        self.privacy_mode: bool = False

    def toggle_privacy_mode(self) -> bool:
        """Toggle ethical face redaction mode."""
        self.privacy_mode = not self.privacy_mode
        return self.privacy_mode

    def detect_and_track(
        self,
        frame: np.ndarray,
        threat_status: str = "SECURE"
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Runs multi-object ByteTrack tracking on frame and renders tactical HUD.

        Args:
            frame: BGR input image.
            threat_status: System threat state ('SECURE', 'BREACH', 'CRITICAL').

        Returns:
            Tuple of (detections_list, tactical_annotated_frame)
        """
        annotated_frame = frame.copy()
        h, w = annotated_frame.shape[:2]
        now = time.time()

        detections: List[Dict[str, Any]] = []

        # Run ByteTrack tracking
        try:
            results = self.model.track(
                frame,
                persist=True,
                conf=self.conf_threshold,
                tracker="bytetrack.yaml",
                verbose=False
            )
        except Exception:
            # Fallback to standard detection if tracker library is re-initializing
            results = self.model(frame, conf=self.conf_threshold, verbose=False)

        if not results or len(results) == 0:
            self._render_tactical_hud(annotated_frame, len(detections), threat_status)
            return detections, annotated_frame

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            self._render_tactical_hud(annotated_frame, 0, threat_status)
            return detections, annotated_frame

        active_track_ids = set()

        for box in boxes:
            conf = float(box.conf[0].item())
            cls_id = int(box.cls[0].item())
            cls_name = self.class_names.get(cls_id, f"cls_{cls_id}")

            coords = box.xyxy[0].tolist()
            x1, y1, x2, y2 = [int(v) for v in coords]

            # Bounding box geometry
            box_w = max(1, x2 - x1)
            box_h = max(1, y2 - y1)
            aspect_ratio = round(box_h / box_w, 2)
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)

            # Track ID extraction
            track_id = int(box.id[0].item()) if (box.id is not None and len(box.id) > 0) else None

            # Dwell duration tracking
            dwell_seconds = 0.0
            if track_id is not None:
                active_track_ids.add(track_id)
                if track_id not in self.track_start_times:
                    self.track_start_times[track_id] = now
                dwell_seconds = round(now - self.track_start_times[track_id], 1)

                if track_id not in self.trajectories:
                    self.trajectories[track_id] = deque(maxlen=self.track_history_len)
                self.trajectories[track_id].append((cx, cy))

            # Privacy Redaction: Blur face/head region if active
            if self.privacy_mode and cls_name.lower() == "person":
                head_y2 = min(y2, y1 + int(box_h * 0.25))
                head_roi = annotated_frame[y1:head_y2, x1:x2]
                if head_roi.shape[0] > 0 and head_roi.shape[1] > 0:
                    blurred_head = cv2.GaussianBlur(head_roi, (45, 45), 25)
                    annotated_frame[y1:head_y2, x1:x2] = blurred_head

            detection_item = {
                "box": (x1, y1, x2, y2),
                "confidence": conf,
                "class_name": cls_name,
                "class_id": cls_id,
                "track_id": track_id,
                "dwell_time": dwell_seconds,
                "aspect_ratio": aspect_ratio,
                "centroid": (cx, cy)
            }
            detections.append(detection_item)

            # Draw trajectory motion trail
            if track_id is not None and track_id in self.trajectories:
                pts = list(self.trajectories[track_id])
                for i in range(1, len(pts)):
                    alpha = i / len(pts)
                    thickness = int(1 + alpha * 2)
                    trail_color = (0, int(255 * alpha), int(255 * (1 - alpha)))
                    cv2.line(annotated_frame, pts[i - 1], pts[i], trail_color, thickness)

            # Draw Tactical Target Reticle
            self._draw_tactical_reticle(
                annotated_frame,
                cls_name,
                conf,
                track_id,
                dwell_seconds,
                aspect_ratio,
                (x1, y1, x2, y2),
                cx, cy
            )

        # Cleanup expired tracks
        for old_id in list(self.track_start_times.keys()):
            if old_id not in active_track_ids and (now - self.track_start_times[old_id]) > 10.0:
                self.track_start_times.pop(old_id, None)
                self.trajectories.pop(old_id, None)

        # Render Top Tactical Command Matrix HUD
        self._render_tactical_hud(annotated_frame, len(detections), threat_status)

        return detections, annotated_frame

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """Compatibility wrapper for standard pipeline."""
        return self.detect_and_track(frame, threat_status="SECURE")

    def _draw_tactical_reticle(
        self,
        img: np.ndarray,
        label: str,
        conf: float,
        track_id: Optional[int],
        dwell: float,
        aspect_ratio: float,
        box: Tuple[int, int, int, int],
        cx: int, cy: int
    ) -> None:
        """Renders corner targeting brackets and scientific telemetry."""
        x1, y1, x2, y2 = box
        bw, bh = x2 - x1, y2 - y1

        # Theme color: Cyan for tracked person, Orange for objects
        color = (0, 245, 212) if label.lower() == "person" else (255, 140, 0)
        line_len = max(8, min(24, int(bw * 0.2)))
        th = 2

        # 1. High-tech Corner Brackets
        # Top-Left
        cv2.line(img, (x1, y1), (x1 + line_len, y1), color, th)
        cv2.line(img, (x1, y1), (x1, y1 + line_len), color, th)
        # Top-Right
        cv2.line(img, (x2, y1), (x2 - line_len, y1), color, th)
        cv2.line(img, (x2, y1), (x2, y1 + line_len), color, th)
        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + line_len, y2), color, th)
        cv2.line(img, (x1, y2), (x1, y2 - line_len), color, th)
        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - line_len, y2), color, th)
        cv2.line(img, (x2, y2), (x2, y2 - line_len), color, th)

        # Center Targeting Dot
        cv2.circle(img, (cx, cy), 3, color, -1)

        # 2. Tactical Metadata Badge
        tid_str = f"TRK#{track_id}" if track_id is not None else "DET"
        badge_text = f"{label.upper()} {tid_str} | {conf:.2f} | H/W:{aspect_ratio:.2f}"
        if dwell > 0:
            badge_text += f" | {dwell}s"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.42
        thickness = 1
        (tw, font_h), baseline = cv2.getTextSize(badge_text, font, font_scale, thickness)

        # Badge pill
        bg_y1 = max(0, y1 - font_h - 8)
        bg_y2 = y1
        cv2.rectangle(img, (x1, bg_y1), (x1 + tw + 10, bg_y2), (15, 23, 42), -1)
        cv2.rectangle(img, (x1, bg_y1), (x1 + tw + 10, bg_y2), color, 1)

        # Badge text
        cv2.putText(
            img,
            badge_text,
            (x1 + 5, bg_y2 - 4),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

    def _render_tactical_hud(
        self,
        img: np.ndarray,
        target_count: int,
        threat_status: str
    ) -> None:
        """Top-screen military command center HUD overlay."""
        h, w = img.shape[:2]
        hud_h = 42

        # Semi-transparent HUD background
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (10, 15, 28), -1)
        cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
        cv2.line(img, (0, hud_h), (w, hud_h), (0, 245, 212), 1)

        # Threat Matrix Color & Text
        threat_color = (0, 255, 120)  # Green
        threat_label = "DEFCON 5 [SECURE]"
        if threat_status == "BREACH":
            threat_color = (0, 215, 255)  # Amber
            threat_label = "DEFCON 3 [PERIMETER BREACH]"
        elif threat_status == "CRITICAL":
            threat_color = (0, 0, 255)  # Red
            threat_label = "DEFCON 1 [CRITICAL INCIDENT]"

        # Left: SU-DRISHTI title & threat level
        cv2.putText(
            img,
            f"SU-DRISHTI TACTICAL C2 // {threat_label}",
            (14, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            threat_color,
            2,
            cv2.LINE_AA,
        )

        # Right: Target Count & Privacy Indicator
        privacy_str = "ETHICAL PRIVACY: [ON]" if self.privacy_mode else "ETHICAL PRIVACY: [OFF]"
        right_text = f"TARGETS: {target_count} | {privacy_str} (Press 'p')"
        font_scale = 0.45
        (tw, _), _ = cv2.getTextSize(right_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.putText(
            img,
            right_text,
            (w - tw - 14, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (200, 220, 240),
            1,
            cv2.LINE_AA,
        )


# Backward compatibility alias
PersonDetector = TacticalDetector
