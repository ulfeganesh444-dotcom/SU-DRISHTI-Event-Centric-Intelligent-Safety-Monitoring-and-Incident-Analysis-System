"""
Screenshot capture utility for SU-DRISHTI.
Saves visual evidence images when incidents/events are detected.
Storage location: screenshots/
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

# Project-relative root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"


def get_screenshots_dir() -> Path:
    """Ensure and return the screenshots directory path."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR


def capture_screenshot(
    frame: np.ndarray,
    object_name: str = "incident",
    overlay_evidence_text: bool = True
) -> str:
    """
    Save the given frame as an evidence screenshot.
    
    Args:
        frame: OpenCV image frame (numpy array).
        object_name: Name of the detected object/event for the filename.
        overlay_evidence_text: Whether to burn timestamp & title into the screenshot for forensic evidence.
        
    Returns:
        Project-relative path string (e.g. 'screenshots/person_20260924_123456_789.jpg').
    """
    screenshots_dir = get_screenshots_dir()
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
    safe_name = "".join(c if c.isalnum() else "_" for c in object_name).lower()
    
    filename = f"{safe_name}_{timestamp_str}.jpg"
    full_path = screenshots_dir / filename
    
    save_frame = frame.copy()
    
    if overlay_evidence_text:
        # Forensic evidence watermark header
        display_time = now.strftime("%Y-%m-%d %H:%M:%S")
        watermark = f"SU-DRISHTI EVIDENCE | {object_name.upper()} | {display_time}"
        
        # Semi-transparent top bar
        h, w = save_frame.shape[:2]
        bar_height = 36
        overlay = save_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, bar_height), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.65, save_frame, 0.35, 0, save_frame)
        
        # Watermark text
        cv2.putText(
            save_frame,
            watermark,
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
            cv2.LINE_AA
        )
    
    cv2.imwrite(str(full_path), save_frame)
    
    # Return normalized relative path for database storage (forward slashes for web/streamlit compatibility)
    relative_path = f"screenshots/{filename}"
    return relative_path
