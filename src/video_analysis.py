"""
SU-DRISHTI — Video Analysis Controller (Day 2).

UI calls this; detection math lives in src/detection/, temporal grouping in
src/incident_store.py. Two research arms, one interface:

  mode="proposed" (default): YOLO -> temporal verification -> ONE incident
                             row per continuous event (extended in place).
  mode="baseline":           YOLO -> immediate frame-level rows, stored as
                             DETECTED (the old behaviour, kept for comparison).

Returns incidents, timeline, summary, report — the dashboard contract that
already exists is unchanged (only additive summary keys).
"""

import time as _time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import cv2

from src.database import init_db
from src.camera import VideoStream
from src.detection.person_detection import TacticalDetector
from src.detection.fall_detection import FallDetector
from src.detection.intrusion_detection import IntrusionDetector
from src.detection.fire_detection import FireDetector
from src.event_filter import EventFilter
from src.incident_engine import IncidentEngine
from src.incident_store import TemporalStore
from src.alerts.screenshot import capture_screenshot
from src.alerts.email_alert import EmailAlertDispatcher
from src.event_logger import save_event
from src.database import update_incident


def _video_time(frame_idx: int, fps: float) -> str:
    total_s = int(frame_idx / max(1.0, fps))
    return f"{total_s // 60:02d}:{total_s % 60:02d}"


def analyze_video(
    video_path: str,
    conf_threshold: float = 0.45,
    cooldown: float = 5.0,
    enable_fall: bool = True,
    enable_intrusion: bool = True,
    enable_fire: bool = False,
    alert_recipient: Optional[str] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    max_frames: Optional[int] = None,
    mode: str = "proposed",
) -> Dict[str, Any]:
    """Analyze a video file end-to-end. Returns incidents, timeline, summary, report.

    Only facts computed by the pipeline are reported — no invented results.
    """
    started_wall = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    t0 = _time.time()
    init_db()

    detector = TacticalDetector(conf_threshold=conf_threshold)
    fall_detector = FallDetector(persistence_frames=4) if enable_fall else None
    intrusion_detector = IntrusionDetector() if enable_intrusion else None
    fire_detector = FireDetector() if enable_fire else None
    emailer = EmailAlertDispatcher()

    stream = VideoStream(source=video_path).start()
    source_label = f"Upload ({Path(video_path).name})"
    fps = stream.get_fps()
    total_frames = stream.get_frame_count()

    store = TemporalStore(
        mode=mode,
        engine=IncidentEngine(),
        event_filter=EventFilter(min_confidence=conf_threshold,
                                 default_cooldown=cooldown),
        save_fn=save_event,
        update_fn=update_incident,
        capture_fn=capture_screenshot,
        dispatcher=emailer,
        fps=fps,
    )

    timeline: List[Dict[str, str]] = []
    incidents: List[Dict[str, Any]] = []
    by_row: Dict[int, Dict[str, Any]] = {}
    max_state: Dict[str, str] = {}
    frames = 0

    def _note(video_t: str, text: str) -> None:
        if len(timeline) < 300:
            timeline.append({"time": video_t, "event": text})

    def _handle(out: Dict[str, Any], vt: str, needs_reasons: bool = True) -> None:
        """Translate one store outcome into timeline + incident list entries."""
        key = out["key"]
        prev = max_state.get(key, "SUSPECTED")
        if out.get("persistence", 1) == 1 and prev == "SUSPECTED" and mode == "proposed":
            _note(vt, f"Candidate observed: {out['event_type']} "
                      f"(confidence {out.get('confidence', 0.0):.2f})")
        if out["state"] == "VERIFYING" and prev == "SUSPECTED" and mode == "proposed":
            _note(vt, f"Verification started: {out['event_type']} "
                      f"({out.get('persistence', 0)}/{out.get('required', 0)} frames)")
        if out["state"] in ("VERIFYING", "CONFIRMED", "DETECTED"):
            if prev not in ("VERIFYING", "CONFIRMED", "DETECTED"):
                max_state[key] = out["state"]
            elif out["state"] == "CONFIRMED":
                max_state[key] = "CONFIRMED"
        if out["action"] == "created":
            _note(vt, f"Incident confirmed: {out['event_type']} "
                      f"[{out.get('risk_level', 'MEDIUM')}, {out.get('confidence', 0.0):.2f}]")
            if out.get("image_path"):
                _note(vt, f"Evidence captured: {out['image_path']}")
            if out.get("alert_status", "not attempted") != "not attempted":
                _note(vt, f"Email alert {out['alert_status']}: {out['event_type']}")
            entry = {
                "db_id": out["row_id"], "event_type": out["event_type"],
                "confidence": out.get("confidence", 0.0),
                "risk_level": out.get("risk_level", "MEDIUM"),
                "risk_score": out.get("risk_score", 0),
                "reasons": out.get("reasons", ["Baseline mode: stored without verification."]),
                "zone": out.get("zone", "MONITORED"),
                "is_night": out.get("is_night", False),
                "duration_sec": out.get("duration_sec", 0.0),
                "persistence": out.get("persistence", 1),
                "required": out.get("required", 1),
                "video_time": vt, "image_path": out.get("image_path", ""),
                "verification": "CONFIRMED" if mode == "proposed" else "DETECTED",
                "suppressed_duplicates": 0,
                "alert_status": out.get("alert_status", "not attempted"),
            }
            incidents.append(entry)
            by_row[out["row_id"]] = entry
        elif out["action"] == "extended":
            entry = by_row.get(out["row_id"])
            if entry is not None:
                entry["duration_sec"] = out.get("duration_sec", entry["duration_sec"])
                entry["confidence"] = max(entry["confidence"],
                                          out.get("confidence", 0.0))

    try:
        while True:
            ret, frame = stream.read()
            if not ret or frame is None:
                break
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
            frame_h, frame_w = frame.shape[:2]
            fidx = stream.get_frame_index()
            vt = _video_time(fidx, fps)

            if progress_cb and total_frames > 0 and frames % 5 == 0:
                progress_cb(min(0.99, frames / total_frames),
                            f"Processing frame {frames}/{total_frames} ...")

            detections, annotated = detector.detect_and_track(frame, threat_status="SECURE")
            person_here = any(d.get("class_name") == "person" for d in detections)
            has_breach = False

            for det in detections:
                cls_name, conf = det["class_name"], det["confidence"]
                box, track_id = det["box"], det.get("track_id")
                if conf < conf_threshold:
                    continue

                in_zone = (intrusion_detector.check_intrusion(box, frame_w, frame_h)
                           if (intrusion_detector and cls_name == "person") else False)
                has_breach = has_breach or in_zone

                is_fall = False
                if fall_detector and cls_name == "person":
                    is_fall = bool(fall_detector.evaluate_person(box, conf, frame_h)["is_fall"])
                    if is_fall:
                        cv2.rectangle(annotated, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 3)

                incident_type = "fall" if is_fall else ("intrusion" if in_zone else cls_name)
                out = store.observe(
                    incident_type, conf, track_id=track_id, frame_idx=fidx,
                    annotated=annotated, source=source_label,
                    in_restricted_zone=in_zone,
                    multi_present=person_here and False,
                    email_recipient=alert_recipient or None)
                _handle(out, vt)

            if fire_detector:
                fire_dets, annotated = fire_detector.detect(annotated)
                for fdet in fire_dets:
                    out = store.observe(
                        "fire", fdet["confidence"], track_id=None, frame_idx=fidx,
                        annotated=annotated, source=source_label,
                        multi_present=person_here,
                        email_recipient=alert_recipient or None)
                    _note(vt, "Verification started: fire") if (
                        out["state"] == "VERIFYING"
                        and max_state.get(out["key"], "SUSPECTED") == "SUSPECTED"
                        and mode == "proposed") else None
                    if out["state"] == "VERIFYING":
                        max_state[out["key"]] = "VERIFYING"
                    _handle(out, vt)

            if intrusion_detector:
                annotated = intrusion_detector.draw_zone(annotated, is_breached=has_breach)
    finally:
        stream.release()

    m = store.metrics()
    confirmed_n = len(incidents)
    high_n = sum(1 for i in incidents if i["risk_level"] == "HIGH")
    crit_n = sum(1 for i in incidents if i["risk_level"] == "CRITICAL")
    raw = m["raw_detections"]
    alert_reduction = round(100.0 * (1.0 - confirmed_n / raw), 1) if raw else 0.0
    dur_s = round(_time.time() - t0, 1)

    summary = {
        "video_file": Path(video_path).name, "analyzed_at": started_wall,
        "mode": mode,
        "frames_analyzed": frames, "raw_detections": raw,
        "candidate_events": m["candidate_events"],
        "confirmed_incidents": confirmed_n,
        "dismissed_candidates": m["dismissed"],
        "rows_extended": m["rows_extended"],
        "confirm_delay_frames_median": m["confirm_delay_frames_median"],
        "confirm_delay_frames_max": m["confirm_delay_frames_max"],
        "high_risk": high_n, "critical": crit_n,
        "duplicates_suppressed": m["suppressed"],
        "alert_reduction_pct": alert_reduction, "processing_sec": dur_s,
    }

    lines = [f"# SU-DRISHTI — Analysis Report [{mode}]", f"Video: {summary['video_file']}",
             f"Analyzed: {started_wall}", f"Frames: {frames} | Raw detections: {raw}",
             f"Candidates: {m['candidate_events']} | Confirmed: {confirmed_n} | "
             f"Dismissed: {m['dismissed']} | Extended: {m['rows_extended']}",
             f"Confirm delay (frames): median {m['confirm_delay_frames_median']}, "
             f"max {m['confirm_delay_frames_max']}",
             f"High: {high_n} | Critical: {crit_n} | Suppressed: {m['suppressed']}",
             f"Alert reduction: {alert_reduction}%", "", "## Confirmed incidents"]
    for i in incidents:
        lines += [f"- {i['event_type']} | risk {i['risk_level']} | conf {i['confidence']:.2f} | "
                  f"video time {i['video_time']} | zone {i['zone']} | "
                  f"duration {i['duration_sec']}s | evidence {i['image_path']} | "
                  f"alert {i['alert_status']} | DB id {i['db_id']}"]
    lines += ["", "## Timeline"]
    lines += [f"- {t['time']}  {t['event']}" for t in timeline]

    if progress_cb:
        progress_cb(1.0, "Analysis complete.")
    return {"incidents": incidents, "timeline": timeline,
            "summary": summary, "report_md": "\n".join(lines)}
