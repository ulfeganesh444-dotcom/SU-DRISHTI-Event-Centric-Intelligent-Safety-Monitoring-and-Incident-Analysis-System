"""
SU-DRISHTI — Intelligent Home Safety & Incident Detection Platform.
Tactical Command & Control Main Entry Point.

Features:
- ByteTrack Persistent Multi-Target Tracking & Motion Trails
- Kinematic Aspect-Ratio Fall Detection
- Polygonal Spatial Geofencing (Intrusion Detection)
- Dwell Time / Loitering Detection
- Tactical HUD & Ethical Privacy Redaction (Toggle with 'p')
- Event Debounce Cooldown Protection
- Forensic Watermarked Evidence & SQLite Persistence

Keyboard Controls during Live Monitoring:
    'q' or ESC : Exit monitoring
    'p'        : Toggle Ethical Privacy Face Redaction (GDPR/Compliance)
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from src.database import init_db
from src.camera import VideoStream
from src.detection.person_detection import TacticalDetector
from src.detection.fall_detection import FallDetector
from src.detection.intrusion_detection import IntrusionDetector
from src.detection.fire_detection import FireDetector
from src.event_filter import EventFilter
from src.incident_engine import IncidentEngine
from src.alerts.screenshot import capture_screenshot
from src.alerts.email_alert import EmailAlertDispatcher
from src.event_logger import save_event


def parse_args():
    parser = argparse.ArgumentParser(
        description="SU-DRISHTI — Tactical Security & Incident Platform"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Capture source: device index (e.g. '0') or video file path (default: '0')",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.45,
        help="Confidence threshold for YOLO detection (default: 0.45)",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=5.0,
        help="Debounce cooldown in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--enable-fall",
        action="store_true",
        default=True,
        help="Enable kinematic fall analysis (default: True)",
    )
    parser.add_argument(
        "--enable-intrusion",
        action="store_true",
        default=True,
        help="Enable virtual tripwire perimeter (default: True)",
    )
    parser.add_argument(
        "--enable-fire",
        action="store_true",
        default=False,
        help="Enable fire detection candidates (default: False)",
    )
    parser.add_argument(
        "--privacy",
        action="store_true",
        default=False,
        help="Start with ethical privacy redaction active",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without displaying OpenCV GUI window",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum frames to process before exit",
    )
    return parser.parse_args()


def run_pipeline(
    source: str = "0",
    conf_threshold: float = 0.45,
    cooldown: float = 5.0,
    enable_fall: bool = True,
    enable_intrusion: bool = True,
    enable_fire: bool = False,
    privacy: bool = False,
    no_gui: bool = False,
    max_frames: int = None,
):
    """Executes the high-precision tactical SU-DRISHTI safety pipeline."""
    print("=" * 70)
    print("SU-DRISHTI — TACTICAL COMMAND & INCIDENT MANAGEMENT SYSTEM")
    print("=" * 70)

    # 1. Initialize SQLite Database
    init_db()
    print("[INIT] Database connection verified at Dashboard/sentinel_ai.db")

    # 2. Initialize Tactical Engines
    print(f"[INIT] Loading YOLOv8n ByteTrack Engine (Conf >= {conf_threshold:.2f})...")
    detector = TacticalDetector(conf_threshold=conf_threshold)
    if privacy:
        detector.toggle_privacy_mode()

    print(f"[INIT] Initializing Debounce Filter (Cooldown: {cooldown}s)...")
    event_filter = EventFilter(min_confidence=conf_threshold, default_cooldown=cooldown)

    print("[INIT] Initializing Incident Verification + Risk Engine...")
    print("        SUSPECTED -> VERIFYING -> CONFIRMED | Risk: LOW/MEDIUM/HIGH/CRITICAL")
    incident_engine = IncidentEngine()

    fall_detector = FallDetector(persistence_frames=4) if enable_fall else None
    intrusion_detector = IntrusionDetector() if enable_intrusion else None
    fire_detector = FireDetector() if enable_fire else None
    email_dispatcher = EmailAlertDispatcher()

    # 3. Ingest Video Stream
    print(f"[INIT] Ingesting stream source: {source}...")
    stream = VideoStream(source=source)
    try:
        stream.start()
    except Exception as e:
        print(f"[ERROR] Failed to start stream from '{source}': {e}")
        return

    source_label = stream.get_source_label()
    print(f"[STATUS] Optical Stream Online: {source_label}")
    print("[HOTKEYS] Press 'q' to Exit | Press 'p' to Toggle Privacy Face Blur\n")

    frame_count = 0
    events_logged = 0
    start_time = time.time()
    current_threat = "SECURE"

    try:
        while True:
            ret, frame = stream.read()
            if not ret or frame is None:
                print("\n[INFO] Stream completed or device disconnected.")
                break

            frame_count += 1
            frame_h, frame_w = frame.shape[:2]

            # Determine threat state for HUD
            threat_level = "SECURE"

            # 1. Run ByteTrack Tactical Detection & Tracking
            detections, annotated_frame = detector.detect_and_track(frame, threat_status=current_threat)

            has_breach = False
            fire_present_this_frame = False
            person_present_this_frame = any(
                d.get("class_name") == "person" for d in detections
            )

            # 2. Safety Kinematics & Spatial Rules
            #    DETECT -> VERIFY (temporal persistence) -> CONTEXT -> RISK
            #    -> CONFIRM (cooldown) -> EVIDENCE -> RECORD
            #    Priority per track: fire > fall > intrusion > person.
            #    ONE event max per track per frame (fixes triple-logging bug).
            for det in detections:
                cls_name = det["class_name"]
                conf = det["confidence"]
                box = det["box"]
                track_id = det.get("track_id")
                dwell = det.get("dwell_time", 0.0)

                if conf < conf_threshold:
                    continue

                in_zone = False
                if intrusion_detector and cls_name == "person":
                    in_zone = intrusion_detector.check_intrusion(box, frame_w, frame_h)
                    if in_zone:
                        has_breach = True

                # Kinematic fall check (draw overlay immediately for demo,
                # but only LOG after incident-engine confirmation below).
                is_fall_frame = False
                fall_info = None
                if fall_detector and cls_name == "person":
                    fall_info = fall_detector.evaluate_person(box, conf, frame_h)
                    is_fall_frame = bool(fall_info["is_fall"])
                    if is_fall_frame:
                        cv2.rectangle(annotated_frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 3)
                        cv2.putText(
                            annotated_frame,
                            f"FALL ALERT [H/W={fall_info['aspect_ratio']}]",
                            (box[0], max(35, box[1] - 12)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.65,
                            (0, 0, 255),
                            2,
                        )

                # Decide the single incident type for this track this frame.
                if is_fall_frame:
                    incident_type = "fall"
                elif in_zone:
                    incident_type = "intrusion"
                else:
                    incident_type = cls_name

                if incident_type == "fall":
                    threat_level = "CRITICAL"
                elif incident_type == "intrusion" and threat_level != "CRITICAL":
                    threat_level = "BREACH"

                multi = person_present_this_frame and fire_present_this_frame

                # Temporal verification + context + risk.
                result = incident_engine.process_event(
                    event_type=incident_type,
                    confidence=conf,
                    track_id=track_id,
                    in_restricted_zone=in_zone,
                    multi_present=multi,
                    detected=True,
                )

                # Show verification state on frame for presentation story.
                if result["state"] in ("VERIFYING", "CONFIRMED") and incident_type in (
                    "fall", "intrusion", "fire",
                ):
                    cv2.putText(
                        annotated_frame,
                        f"{incident_type.upper()}: {result['state']} "
                        f"{result['persistence']}/{result['required']} | {result['risk_level']}",
                        (box[0], max(55, box[1] - 32)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255) if result["state"] == "CONFIRMED" else (0, 215, 255),
                        1,
                        cv2.LINE_AA,
                    )

                # CONFIRM: persistence met AND cooldown passed AND legacy
                # confidence/cooldown gate passes (defence in depth).
                if result["should_alert"] and event_filter.should_log(incident_type, conf):
                    ev_path = capture_screenshot(annotated_frame, incident_type)
                    save_event(
                        incident_type, result["confidence"], source_label,
                        image_path=ev_path,
                        risk_level=result["risk_level"],
                        event_status="CONFIRMED",
                        zone=result["zone"],
                        duration_sec=result["duration_sec"],
                    )
                    if result["risk_level"] in ("HIGH", "CRITICAL"):
                        email_dispatcher.send_alert(
                            incident_type, result["confidence"],
                            time.strftime("%Y-%m-%d %H:%M:%S"),
                            ev_path, result["risk_level"],
                        )
                    events_logged += 1

            # Check D: Fire Detection (if enabled) — also via incident engine.
            if fire_detector:
                fire_dets, annotated_frame = fire_detector.detect(annotated_frame)
                for fdet in fire_dets:
                    fire_present_this_frame = True
                    threat_level = "CRITICAL"
                    multi = person_present_this_frame and True
                    result = incident_engine.process_event(
                        event_type="fire",
                        confidence=fdet["confidence"],
                        track_id=None,
                        in_restricted_zone=False,
                        multi_present=person_present_this_frame,
                        detected=True,
                    )
                    if result["should_alert"] and event_filter.should_log("fire", fdet["confidence"]):
                        ev_path = capture_screenshot(annotated_frame, "fire")
                        save_event(
                            "fire", result["confidence"], source_label,
                            image_path=ev_path,
                            risk_level=result["risk_level"],
                            event_status="CONFIRMED",
                            zone=result["zone"],
                            duration_sec=result["duration_sec"],
                        )
                        events_logged += 1

            current_threat = threat_level

            # Draw Intrusion Zone overlay
            if intrusion_detector:
                annotated_frame = intrusion_detector.draw_zone(annotated_frame, is_breached=has_breach)

            # GUI Rendering Loop
            if not no_gui:
                elapsed = max(0.001, time.time() - start_time)
                fps = frame_count / elapsed
                bottom_status = f"SYS_STATUS: ACTIVE | FPS: {fps:.1f} | FRAMES: {frame_count} | INCIDENTS: {events_logged}"
                cv2.putText(
                    annotated_frame,
                    bottom_status,
                    (14, frame_h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (0, 245, 212),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("SU-DRISHTI — Tactical Command Display", annotated_frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    print("\n[INFO] Operator requested shutdown.")
                    break
                elif key in (ord("p"), ord("P")):
                    is_active = detector.toggle_privacy_mode()
                    print(f"[SECURITY] Ethical Privacy Redaction: {'ENABLED' if is_active else 'DISABLED'}")

            if max_frames is not None and frame_count >= max_frames:
                print(f"\n[INFO] Reached requested max_frames ({max_frames}). Stopping.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by keyboard.")
    finally:
        stream.release()
        total_time = max(0.001, time.time() - start_time)
        print("\n" + "=" * 70)
        print("TACTICAL MISSION REPORT")
        print(f"Total Optical Frames   : {frame_count}")
        print(f"Total Incidents Logged : {events_logged}")
        print(f"Operational Throughput : {frame_count/total_time:.1f} FPS (Time: {total_time:.2f}s)")
        print("=" * 70)


def main():
    args = parse_args()
    run_pipeline(
        source=args.source,
        conf_threshold=args.conf,
        cooldown=args.cooldown,
        enable_fall=args.enable_fall,
        enable_intrusion=args.enable_intrusion,
        enable_fire=args.enable_fire,
        privacy=args.privacy,
        no_gui=args.no_gui,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    main()
