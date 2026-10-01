"""
SU-DRISHTI — Temporal incident store (Day 2).

Single authority for turning per-frame detections into stored incidents.

Two modes, same interface (research comparison arms):
  mode="proposed": DETECTED -> VERIFYING -> CONFIRMED via IncidentEngine;
                   one continuous occurrence = ONE row, extended in place
                   (end_time/duration grow, evidence stays at first confirm).
  mode="baseline": every filter-passing detection is stored immediately as
                   event_status DETECTED (the old frame-level behaviour),
                   kept runnable for comparison. No verification performed.

Duplicate prevention happens HERE (open-incident extension + cooldown +
frame-gap closure), never by deleting rows afterwards.

All side effects (save/update/capture/email) are injected callables so the
logic is unit-testable without a database, camera, or network.
"""

import time as _time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.incident_engine import IncidentEngine
from src.event_filter import EventFilter


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class TemporalStore:
    """Groups repeated detections of one ongoing event into one incident row."""

    def __init__(
        self,
        mode: str = "proposed",
        engine: Optional[IncidentEngine] = None,
        event_filter: Optional[EventFilter] = None,
        save_fn: Optional[Callable[..., int]] = None,
        update_fn: Optional[Callable[..., None]] = None,
        capture_fn: Optional[Callable[[Any, str], str]] = None,
        email_fn: Optional[Callable[..., bool]] = None,
        dispatcher: Any = None,
        email_sender: Optional[Callable[[Dict[str, Any]], str]] = None,
        fps: float = 30.0,
        reopen_gap_frames: int = 45,
        close_gap_frames: int = 45,
        conf_threshold: float = 0.45,
    ):
        if mode not in ("proposed", "baseline"):
            raise ValueError("mode must be 'proposed' or 'baseline'")
        self.mode = mode
        self.engine = engine or IncidentEngine()
        self.event_filter = event_filter or EventFilter()
        self.save_fn = save_fn
        self.update_fn = update_fn
        self.capture_fn = capture_fn
        self.email_fn = email_fn  # legacy direct callback (kept for tests)
        self.dispatcher = dispatcher
        self.email_sender = email_sender  # fn(incident_dict) -> SENT/FAILED/NOT_SENT
        self.fps = max(1.0, float(fps))
        self.reopen_gap_frames = int(reopen_gap_frames)
        self.close_gap_frames = int(close_gap_frames)
        self.conf_threshold = float(conf_threshold)

        # key -> {row_id, first_frame, last_seen, row_last_frame, best_conf,
        #         max_state, source, event_type}
        self._open: Dict[str, Dict[str, Any]] = {}
        self.raw = 0
        self.rows_created = 0
        self.rows_extended = 0
        self.suppressed = 0
        self.delays: List[int] = []

    # ------------------------------------------------------------- helpers --
    def _sweep(self, frame_idx: int) -> None:
        """Forget keys unseen for longer than close_gap_frames (event ended)."""
        stale = [k for k, s in self._open.items()
                 if frame_idx - s["last_seen"] > self.close_gap_frames]
        for k in stale:
            del self._open[k]

    # ---------------------------------------------------------------- main --
    def observe(
        self,
        event_type: str,
        confidence: float,
        track_id: Any = None,
        frame_idx: int = 0,
        annotated: Any = None,
        source: str = "",
        in_restricted_zone: bool = False,
        multi_present: bool = False,
        email_recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Feed one per-frame detection. Returns an outcome dict for timeline."""
        self.raw += 1
        et = str(event_type).lower()
        self._sweep(frame_idx)

        if self.mode == "baseline":
            return self._observe_baseline(et, confidence, track_id, frame_idx,
                                          source, email_recipient)
        return self._observe_proposed(et, confidence, track_id, frame_idx,
                                      annotated, source, in_restricted_zone,
                                      multi_present, email_recipient)

    # -------------------------------------------------------------- baseline --
    def _observe_baseline(self, et, conf, track_id, frame_idx, source,
                          email_recipient) -> Dict[str, Any]:
        key = f"{et}#{track_id if track_id is not None else 'global'}"
        slot = self._open.setdefault(key, {
            "row_id": None, "first_frame": frame_idx, "last_seen": frame_idx,
            "row_last_frame": -10 ** 9, "best_conf": 0.0,
            "max_state": "DETECTED", "source": source, "event_type": et})
        slot["last_seen"] = frame_idx
        slot["best_conf"] = max(slot["best_conf"], float(conf))
        if self.event_filter.should_log(et, conf) and self.save_fn is not None:
            row_id = self.save_fn(
                et, slot["best_conf"], source, event_time=_now_str(), image_path="",
                risk_level="MEDIUM", event_status="DETECTED", zone="MONITORED",
                duration_sec=0.0, end_time="")
            self.rows_created += 1
            return {"key": key, "event_type": et, "state": "DETECTED",
                    "persistence": 1, "required": 1, "risk_level": "MEDIUM",
                    "action": "created", "row_id": row_id,
                    "confidence": slot["best_conf"]}
        return {"key": key, "event_type": et, "state": "DETECTED",
                "persistence": 1, "required": 1, "risk_level": "MEDIUM",
                "action": "none", "confidence": slot["best_conf"]}

    # -------------------------------------------------------------- proposed --
    def _observe_proposed(self, et, conf, track_id, frame_idx, annotated,
                          source, in_zone, multi, email_recipient) -> Dict[str, Any]:
        res = self.engine.process_event(
            et, conf, track_id=track_id, in_restricted_zone=in_zone,
            multi_present=multi, detected=True)
        key = res["key"]
        slot = self._open.setdefault(key, {
            "row_id": None, "first_frame": frame_idx, "last_seen": frame_idx,
            "row_last_frame": -10 ** 9, "best_conf": 0.0,
            "max_state": "SUSPECTED", "source": source, "event_type": et})
        slot["last_seen"] = frame_idx
        slot["best_conf"] = max(slot["best_conf"], float(conf))
        if res["state"] == "VERIFYING" and slot["max_state"] == "SUSPECTED":
            slot["max_state"] = "VERIFYING"

        out: Dict[str, Any] = {
            "key": key, "event_type": et, "state": res["state"],
            "persistence": res["persistence"], "required": res["required"],
            "risk_level": res["risk_level"], "risk_score": res["risk_score"],
            "reasons": res["reasons"], "confidence": res["confidence"],
            "zone": res["zone"], "is_night": res["is_night"],
            "action": "none",
        }

        if res["state"] == "CONFIRMED" and not res["should_alert"]:
            self.suppressed += 1
            slot["max_state"] = "CONFIRMED"
            return out
        if not (res["should_alert"]
                and self.event_filter.should_log(et, conf)):
            return out

        slot["max_state"] = "CONFIRMED"
        duration_frames = frame_idx - slot["first_frame"] + 1
        duration_sec = round(duration_frames / self.fps, 2)
        wall = _now_str()

        # Same continuous event still open -> EXTEND the row in place.
        if (slot["row_id"] is not None
                and frame_idx - slot["row_last_frame"] <= self.reopen_gap_frames
                and self.update_fn is not None):
            self.update_fn(slot["row_id"], end_time=wall,
                            duration_sec=duration_sec,
                            confidence=slot["best_conf"])
            slot["row_last_frame"] = frame_idx
            self.rows_extended += 1
            out.update({"action": "extended", "row_id": slot["row_id"],
                        "duration_sec": duration_sec})
            return out

        # Genuinely new incident -> evidence + row + (selective) email.
        ev_path = self.capture_fn(annotated, et) if self.capture_fn else ""
        row_id = self.save_fn(
            et, slot["best_conf"], source, event_time=wall, image_path=ev_path,
            risk_level=res["risk_level"], event_status="CONFIRMED",
            zone=res["zone"], duration_sec=duration_sec,
            end_time=wall) if self.save_fn else -1
        slot["row_id"] = row_id
        slot["row_last_frame"] = frame_idx
        self.rows_created += 1
        self.delays.append(frame_idx - slot["first_frame"])

        alert_status = "not attempted"
        # ONE confirmed incident = ONE email: this branch runs only when a
        # brand-new row is inserted (extensions never reach here). Every
        # CONFIRMED risk tier is emailed; VERIFYING never is.
        if self.email_fn is not None or self.dispatcher is not None \
                or self.email_sender is not None:
            # Email failure must never break the pipeline.
            try:
                from src.alerts.email_alert import send_incident_email
                incident = {
                    "event_type": et, "confidence": slot["best_conf"],
                    "start_time": wall, "event_time": wall, "end_time": wall,
                    "duration_sec": duration_sec, "source": source,
                    "risk_level": res["risk_level"], "status": "CONFIRMED",
                    "image_path": ev_path, "recipient": email_recipient or None,
                }
                if self.email_sender is not None:
                    email_status = self.email_sender(incident)
                elif self.email_fn is not None:
                    sent = bool(self.email_fn(
                        et, slot["best_conf"], wall, ev_path, res["risk_level"],
                        recipient=email_recipient or None,
                        start_time=wall, end_time=wall, duration_sec=duration_sec,
                        source=source, status="CONFIRMED"))
                    email_status = "SENT" if sent else "FAILED"
                else:
                    email_status = send_incident_email(
                        incident, dispatcher=self.dispatcher,
                        recipient=email_recipient or None)
                alert_status = {"SENT": "sent", "FAILED": "failed",
                                "NOT_SENT": "not configured"}.get(email_status, "failed")
            except Exception as e:
                print(f"[ALERT ERROR] email callback failed: {e}")
                alert_status = "failed"

        out.update({"action": "created", "row_id": row_id,
                    "duration_sec": duration_sec,
                    "delay_frames": frame_idx - slot["first_frame"],
                    "image_path": ev_path, "alert_status": alert_status})
        return out

    # -------------------------------------------------------------- metrics --
    def metrics(self) -> Dict[str, Any]:
        cands = [s for s in self._open.values()
                 if s["max_state"] in ("VERIFYING", "CONFIRMED")]
        logged = [s for s in self._open.values() if s["row_id"] is not None]
        delays = sorted(self.delays)
        med = delays[len(delays) // 2] if delays else 0
        return {
            "raw_detections": self.raw,
            "candidate_events": len(cands),
            "rows_created": self.rows_created,
            "rows_extended": self.rows_extended,
            "suppressed": self.suppressed,
            "dismissed": len(cands) - len(logged),
            "confirm_delay_frames_median": med,
            "confirm_delay_frames_max": max(delays) if delays else 0,
        }
