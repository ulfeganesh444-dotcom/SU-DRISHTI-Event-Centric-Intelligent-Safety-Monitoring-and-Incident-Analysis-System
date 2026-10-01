"""
Video Detection runner for SU-DRISHTI.
Processes uploaded pre-recorded video files through the standard event pipeline.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from src.main import run_pipeline


def process_video_file(
    video_path: str,
    conf_threshold: float = 0.50,
    cooldown: float = 4.0,
    no_gui: bool = True,
    max_frames: Optional[int] = None
) -> None:
    """
    Process an uploaded or stored video file through the core SU-DRISHTI pipeline.

    Args:
        video_path: Path to the target video file.
        conf_threshold: Confidence threshold for YOLO detection.
        cooldown: Cooldown in seconds between events of the same class.
        no_gui: True to suppress OpenCV window display.
        max_frames: Optional limit on processed frames.
    """
    vpath = Path(video_path)
    if not vpath.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    print(f"[VIDEO PROCESSOR] Initiating analysis on: {vpath.name}")
    run_pipeline(
        source=str(vpath),
        conf_threshold=conf_threshold,
        cooldown=cooldown,
        no_gui=no_gui,
        max_frames=max_frames
    )


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "videos/demo_person.mp4"
    process_video_file(target, no_gui=False)
