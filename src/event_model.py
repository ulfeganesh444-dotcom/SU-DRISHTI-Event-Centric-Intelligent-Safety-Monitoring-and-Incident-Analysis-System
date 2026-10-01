"""
SU-DRISHTI — Event/Incident data model (Day 1 architecture preparation).

STATUS: interfaces and documentation only. Nothing here runs in the live
pipeline yet. The current system (IncidentEngine + events table) is untouched.
Day 2/Day 3 will implement builders/consumers against these interfaces.

Research pipeline being prepared:
    INPUT -> DETECTION -> TEMPORAL EVIDENCE -> CONTEXT -> INCIDENT FORMATION
    -> CONFIDENCE/UNCERTAINTY -> HUMAN REVIEW (if needed) -> EVIDENCE
    -> INCIDENT RECORD -> ALERT/REPORT
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventState(str, Enum):
    """Future lifecycle states. Today these are architectural labels only —
    the live pipeline currently produces SUSPECTED/VERIFYING/CONFIRMED via
    IncidentEngine and NEW/ACKNOWLEDGED/RESOLVED operator status."""

    DETECTED = "DETECTED"          # single-frame raw observation
    SUSPECTED = "SUSPECTED"        # repeated observation, not yet persistent
    VERIFYING = "VERIFYING"        # persistence/context checks in progress
    CONFIRMED = "CONFIRMED"        # verified incident, stored with evidence
    HUMAN_REVIEW = "HUMAN_REVIEW"  # uncertain: needs operator judgement
    RESOLVED = "RESOLVED"          # reviewed / handled by operator


class ReviewStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"  # confident incident, auto-filed
    PENDING = "PENDING"            # queued for operator review
    REVIEWED = "REVIEWED"          # operator has judged the incident


@dataclass
class Incident:
    """Future incident-level record. One Incident groups many repeated
    per-frame detections of the same occurrence (incident formation)."""

    incident_id: Optional[int] = None
    event_type: str = ""           # e.g. person, intrusion, fall, fire
    confidence: float = 0.0        # best supporting detection confidence
    start_time: str = ""           # first supporting observation (YYYY-MM-DD HH:MM:SS)
    end_time: str = ""             # last supporting observation
    duration: float = 0.0          # seconds, end_time - start_time
    source: str = ""               # e.g. Upload (video.mp4), Webcam (Device 0)
    status: str = EventState.DETECTED.value
    risk_level: str = "MEDIUM"     # LOW / MEDIUM / HIGH / CRITICAL (project-defined)
    evidence_path: str = ""        # screenshot / video segment path
    review_status: str = ReviewStatus.NOT_REQUIRED.value

    def to_record(self) -> Dict[str, Any]:
        """Serialize to the existing `events` table layout (no schema change).

        Mapping (Day 1, backward-compatible):
          incident_id   -> id            event_type -> object_name
          confidence    -> confidence    start_time -> event_time
          end_time      -> (Day 2 column, currently carried in duration/notes)
          duration      -> duration_sec  source     -> source
          status        -> event_status  risk_level -> risk_level
          evidence_path -> image_path    review_status -> notes (Day 2: own column)
        """
        return {
            "object_name": self.event_type,
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "event_time": self.start_time,
            "image_path": self.evidence_path,
            "severity": self.risk_level,
            "risk_level": self.risk_level,
            "event_status": self.status,
            "zone": "MONITORED",
            "duration_sec": float(self.duration),
            "status": "NEW",
            "notes": f"review={self.review_status};end={self.end_time}",
        }

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "Incident":
        """Rebuild an Incident view from an existing `events` row (read-only)."""
        return Incident(
            incident_id=row.get("id"),
            event_type=row.get("object_name", ""),
            confidence=float(row.get("confidence", 0.0) or 0.0),
            start_time=row.get("event_time", ""),
            end_time="",
            duration=float(row.get("duration_sec", 0.0) or 0.0),
            source=row.get("source", ""),
            status=row.get("event_status", EventState.DETECTED.value),
            risk_level=row.get("risk_level", "MEDIUM"),
            evidence_path=row.get("image_path", ""),
        )


class IncidentBuilder:
    """Interface (not yet implemented) for Day 2: group a stream of dated,
    typed detections into Incident objects with temporal evidence, context,
    confidence/uncertainty gating and optional HUMAN_REVIEW routing.

    def observe(self, event_type, confidence, timestamp, context) -> None: ...
    def poll_ready(self) -> List[Incident]: ...   # CONFIRMED or HUMAN_REVIEW
    def dismiss_stale(self) -> List[Incident]: ...  # expired candidates
    """

    def observe(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Day 2 task: temporal grouping of detections.")

    def poll_ready(self) -> List[Incident]:
        raise NotImplementedError("Day 2 task: emit confirmed/review incidents.")

    def dismiss_stale(self) -> List[Incident]:
        raise NotImplementedError("Day 2 task: expire unconfirmed candidates.")


# Uncertainty gate placeholder values (to be calibrated experimentally Day 2+).
REVIEW_CONFIDENCE_BAND = (0.45, 0.65)  # inside band -> candidate for HUMAN_REVIEW
