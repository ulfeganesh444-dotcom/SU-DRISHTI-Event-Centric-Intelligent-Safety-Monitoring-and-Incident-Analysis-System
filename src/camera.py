"""
Camera stream handler for SU-DRISHTI.
Provides clean capture abstraction for live webcams, RTSP streams, and pre-recorded video files.
"""

from typing import Union, Optional, Tuple
import cv2
import numpy as np


class VideoStream:
    """
    Unified video capture wrapper for OpenCV VideoCapture.
    Supports webcam indices (e.g. 0, 1) and video file paths.
    """

    def __init__(self, source: Union[int, str] = 0):
        """
        Args:
            source: Camera device index (int) or path to video file (str).
        """
        self.source = source
        self.cap: Optional[cv2.VideoCapture] = None
        self._is_opened = False

    def start(self) -> "VideoStream":
        """Open the video capture source."""
        # Convert numeric string to int if passed via CLI (e.g. "0" -> 0)
        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open video source: {self.source}")

        self._is_opened = True
        return self

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the next frame from the stream.

        Returns:
            Tuple (success: bool, frame: np.ndarray or None)
        """
        if not self._is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        return ret, frame

    def release(self) -> None:
        """Release the capture device and clean up resources."""
        if self.cap is not None:
            self.cap.release()
            self._is_opened = False
        cv2.destroyAllWindows()

    def get_fps(self) -> float:
        """Return source frame rate (video files). Falls back to 30.0."""
        if self.cap is not None:
            fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps > 0:
                return fps
        return 30.0

    def get_frame_index(self) -> int:
        """Return 0-based index of the last read frame (video files)."""
        if self.cap is not None:
            return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        return 0

    def get_frame_count(self) -> int:
        """Return total frame count if known, else 0."""
        if self.cap is not None:
            return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return 0

    def get_source_label(self) -> str:
        """Return human-readable source label (e.g. 'Webcam' or filename)."""
        if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
            return f"Webcam (Device {self.source})"
        return f"Video ({self.source})"
