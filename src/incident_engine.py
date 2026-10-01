"""
SU-DRISHTI — Incident Verification + Context + Risk Engine.

Pipeline stage:
    DETECTION -> VERIFY -> CONTEXT -> RISK -> CONFIRM -> EVIDENCE -> RECORD

Design goals (2-day constraint):
- No new dependencies, no new DL models. Pure Python rule-based logic.
- Detection != Event. A detection becomes an event only after temporal
  persistence (consecutive frames) AND cooldown debouncing.
- States: SUSPECTED -> VERIFYING -> CONFIRMED
- Risk: LOW / MEDIUM / HIGH / CRITICAL with explainable reasons.
- Context: EVENT + TIME + ZONE + PERSISTENCE (rule-based, no overclaim).

Usage in main.py:
    engine = IncidentEngine()
    result = engine.process_event(
        event_type="intrusion", confidence=0.86, track_id=3,
        in_restricted_zone=True, frame_w=640, frame_h=480,
        multi_present=False, detected=True,
    )
    if result["should_alert"]:
        capture screenshot, save_event(... risk_level=result["risk_level"] ...)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple, List, Optional


# ---------------------------------------------------------------------------
# Configuration (tuned for laptop CPU, 15-30 FPS webcam / video file)
# ---------------------------------------------------------------------------

# Consecutive frames a detection must persist before CONFIRMED.
REQUIRED_FRAMES = {
    "person": 5,
    "intrusion": 3,
    "fall": 4,
    "fire": 6,
    "knife": 3,
}

# Seconds before the SAME incident key can create another DB event.
# NOTE: person cooldown is intentionally long (30s) to fix the
# "hundreds of person_*.jpg screenshots" database-flood problem.
EVENT_COOLDOWN = {
    "person": 30.0,
    "intrusion": 15.0,
    "fall": 15.0,
    "fire": 10.0,
    "knife": 10.0,
}

# Base risk score per event type (0-100 scale, before modifiers).
BASE_RISK = {
    "person": 10,
    "intrusion": 50,
    "fall": 50,
    "fire": 65,
    "knife": 80,
    "dog": 5,
    "cat": 5,
    "car": 15,
    "backpack": 10,
}

# Night window for context awareness (configurable restricted hours).
NIGHT_START_HOUR = 22  # 10 PM
NIGHT_END_HOUR = 6     # 6 AM

MAX_MISSING_FRAMES = 8  # forget a track after this many unseen frames


@dataclass
class TrackState:
    consecutive_frames: int = 0
    missing_frames: int = 0
    state: str = "SUSPECTED"
    first_seen: float = field(default_factory=time.time)
    best_confidence: float = 0.0
    last_confirm_time: float = 0.0


class IncidentEngine:
    """
    Stateful temporal verification + context + risk engine.

    One instance lives for the whole monitoring session (see main.py).
    Keyed by (event_type, track_id or 'global') so two different people
    are verified independently.
    """

    def __init__(
        self,
        required_frames: Optional[Dict[str, int]] = None,
        cooldowns: Optional[Dict[str, float]] = None,
        night_start: int = NIGHT_START_HOUR,
        night_end: int = NIGHT_END_HOUR,
    ):
        self.required_frames = dict(REQUIRED_FRAMES)
        if required_frames:
            self.required_frames.update(required_frames)
        self.cooldowns = dict(EVENT_COOLDOWN)
        if cooldowns:
            self.cooldowns.update(cooldowns)
        self.night_start = night_start
        self.night_end = night_end
        self._tracks: Dict[str, TrackState] = {}

    # ------------------------------------------------------------------
    @staticmethod
    def _make_key(event_type: str, track_id) -> str:
        tid = str(track_id) if track_id is not None else "global"
        return f"{event_type.lower()}#{tid}"

    def required_for(self, event_type: str) -> int:
        return self.required_frames.get(event_type.lower(), 5)

    def cooldown_for(self, event_type: str) -> float:
        return self.cooldowns.get(event_type.lower(), 15.0)

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def is_night(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        h = now.hour
        if self.night_start <= self.night_end:
            return self.night_start <= h < self.night_end
        return h >= self.night_start or h < self.night_end

    @staticmethod
    def zone_label(in_restricted_zone: bool) -> str:
        return "RESTRICTED" if in_restricted_zone else "MONITORED"

    # ------------------------------------------------------------------
    # Risk engine — explainable, project-defined prioritization.
    # NOT a medical diagnosis or guaranteed prediction.
    # ------------------------------------------------------------------
    def compute_risk(
        self,
        event_type: str,
        confidence: float,
        duration_sec: float,
        zone: str,
        is_night: bool,
        multi_present: bool = False,
    ) -> Tuple[str, int, List[str]]:
        et = event_type.lower()
        score = float(BASE_RISK.get(et, 20))
        reasons: List[str] = [f"Base score for '{et}': {BASE_RISK.get(et, 20)}"]

        conf_bonus = round(float(confidence) * 20, 1)
        score += conf_bonus
        reasons.append(f"Detection confidence {confidence:.2f} -> +{conf_bonus}")

        dur_bonus = min(float(duration_sec) * 2.0, 15.0)
        if dur_bonus > 0.5:
            score += dur_bonus
            reasons.append(f"Persistence {duration_sec:.1f}s -> +{dur_bonus:.1f}")

        if zone == "RESTRICTED":
            score += 15
            reasons.append("Inside configured restricted zone -> +15")

        if is_night:
            score += 10
            reasons.append("Restricted hours (night) -> +10")

        if multi_present:
            score += 20
            reasons.append("Multiple relevant detections together -> +20")

        score_int = int(min(100, round(score)))

        if score_int >= 80:
            level = "CRITICAL"
        elif score_int >= 55:
            level = "HIGH"
        elif score_int >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"
        reasons.append(f"Total {score_int}/100 -> {level}")
        return level, score_int, reasons

    # ------------------------------------------------------------------
    # Main entry: feed ONE candidate detection per frame.
    # ------------------------------------------------------------------
    def process_event(
        self,
        event_type: str,
        confidence: float,
        track_id=None,
        in_restricted_zone: bool = False,
        multi_present: bool = False,
        detected: bool = True,
        now: Optional[float] = None,
    ) -> Dict:
        et = event_type.lower()
        now_ts = now if now is not None else time.time()
        key = self._make_key(et, track_id)
        st = self._tracks.get(key)
        if st is None:
            st = TrackState(first_seen=now_ts)
            self._tracks[key] = st

        if detected:
            st.consecutive_frames += 1
            st.missing_frames = 0
            st.best_confidence = max(st.best_confidence, float(confidence))
        else:
            st.missing_frames += 1
            if st.missing_frames > MAX_MISSING_FRAMES:
                st.consecutive_frames = 0
                st.state = "SUSPECTED"
                st.best_confidence = 0.0
                st.first_seen = now_ts

        required = self.required_for(et)
        if st.consecutive_frames >= required:
            st.state = "CONFIRMED"
        elif st.consecutive_frames >= 2:
            st.state = "VERIFYING"
        else:
            st.state = "SUSPECTED"

        duration = now_ts - st.first_seen
        zone = self.zone_label(in_restricted_zone)
        night = self.is_night(datetime.fromtimestamp(now_ts))
        risk_level, risk_score, reasons = self.compute_risk(
            et, st.best_confidence or confidence, duration,
            zone, night, multi_present,
        )

        # Duplicate-event prevention: CONFIRMED still needs cooldown.
        should_alert = False
        if st.state == "CONFIRMED":
            elapsed = now_ts - st.last_confirm_time
            if elapsed >= self.cooldown_for(et):
                st.last_confirm_time = now_ts
                should_alert = True

        return {
            "key": key,
            "event_type": et,
            "state": st.state,               # SUSPECTED | VERIFYING | CONFIRMED
            "persistence": st.consecutive_frames,
            "required": required,
            "duration_sec": round(duration, 1),
            "zone": zone,
            "is_night": night,
            "risk_level": risk_level,        # LOW | MEDIUM | HIGH | CRITICAL
            "risk_score": risk_score,
            "reasons": reasons,
            "confidence": round(st.best_confidence or confidence, 4),
            "should_alert": should_alert,
        }

    def reset(self) -> None:
        self._tracks.clear()
