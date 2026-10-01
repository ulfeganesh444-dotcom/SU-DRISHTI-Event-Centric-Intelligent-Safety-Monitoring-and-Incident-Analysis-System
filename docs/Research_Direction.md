# SU-DRISHTI — Research Direction
> See Beyond Vision, Protect Beyond Detection.

**Status: Day 1 — proposed research direction. Nothing in sections 5–10 is
experimentally validated yet. The only running system is the baseline in §2.**

## 1. Problem
Continuous camera monitoring produces a flood of noisy per-frame detections.
Human operators suffer alert fatigue: hundreds of near-identical observations
(one person standing in view for a minute ≈ hundreds of raw detections) bury
the few observations that actually deserve attention. Raw CCTV records
everything; naive detectors alarm on everything. Neither converts a continuous
observation stream into a small set of reliable, reviewable safety incidents.

## 2. Existing baseline (running today, measured — not claimed)
Current approach: **Video → YOLOv8n detection → confidence/whitelist filter →
per-type cooldown debounce → screenshot evidence → SQLite event log →
Streamlit dashboard.**
- Verification is frame-persistence only (SUSPECTED → VERIFYING → CONFIRMED
  over N consecutive frames; N = 3–6 by event type).
- Risk is a fixed rule table (confidence + persistence + zone + time-of-day +
  co-occurrence), project-defined, not a diagnosis.
- Deduplication is time-cooldown per event type (e.g. person 30 s).
- Known limits: single global track state per (type, track-id); no end-time
  tracking; no uncertainty routing (everything is auto-filed); zone is one
  fixed polygon; evaluation so far is functional (pipeline runs), not
  experimental (no precision/recall/false-alarm measurement yet).

## 3. Research question
“Can continuous and noisy visual detections be converted into reliable,
coherent, event-level safety incidents while reducing redundant or
unnecessary alerts?”

## 4. Proposed system concept
```
INPUT (recorded video / webcam / IP camera)
  → DETECTION (object/event candidates per frame)
  → TEMPORAL EVIDENCE (persistence across frames)
  → CONTEXT (zone, time, co-occurring detections)
  → INCIDENT FORMATION (group repeats into ONE event with start/end/duration)
  → CONFIDENCE / UNCERTAINTY (reliable → file; uncertain → human review)
  → HUMAN REVIEW (only when necessary)
  → EVIDENCE (screenshot / relevant segment, preserved with the record)
  → INCIDENT RECORD (structured database row)
  → ALERT / REPORT (risk-prioritized)
```
Day 1 delivers the interfaces for this pipeline (`src/event_model.py`);
Day 2/3 will implement one stage at a time behind them.

## 5. Event-level incident formation (proposed)
Replace “one detection ≈ one row” with: many dated detections of the same
occurrence → single `Incident` (incident_id, event_type, start/end_time,
duration, source, status, risk, evidence, review_status). Repeated frames
extend the open incident instead of creating rows; cooldowns become
incident-closure rules. Mapping to the current `events` table is documented
in `Incident.to_record()` — no schema change required on Day 1.

## 6. Temporal verification (proposed)
Persistence thresholds per event class, plus explicit candidate expiry
(DISMISSED outlet already counted in analysis summaries). Future work:
adaptive thresholds from measured false-alarm rates instead of fixed constants.

## 7. Context analysis (proposed)
Zone rules, time-of-day, and co-occurrence (e.g. fire + person present)
remain the context signals; Day 2 will log them per incident as structured
fields so their contribution can be ablated in experiments.

## 8. Uncertainty / human review (proposed)
Detections inside a calibrated confidence band, or with conflicting context,
route to HUMAN_REVIEW instead of auto-filing. Operator judgement
(reviewed / false alarm) is recorded and becomes labelled data for evaluation.
Placeholder band `(0.45, 0.65)` in `event_model.py` is NOT calibrated.

## 9. Evidence preservation (proposed)
Every confirmed or reviewed incident keeps its supporting evidence
(screenshot today; short video segment later) with timestamp, confidence,
risk and verification trail, so any alert can answer “why was this flagged?”
from stored facts.

## 10. Evaluation plan (proposed, not yet run)
- Dataset: fixed recorded clips with hand-labelled incident intervals
  (start/end, type). No synthetic metrics.
- Baseline vs proposed on the same clips: incidents reported, duplicate rows
  per true incident, false alarms, missed incidents, median detection-to-file
  latency, operator actions needed.
- Report raw counts first; only then derived rates. No improvement
  percentages will be stated before both arms are measured.

## 11. Research limitations (acknowledged upfront)
- Prototype on a laptop CPU; single fixed camera view; one zone polygon.
- Fall analysis is bounding-box kinematics, not medical validation.
- Chromatic fire detection is a candidate detector, not a certified alarm.
- Risk levels are project-defined priorities, not safety guarantees.
- SU-DRISHTI assists monitoring; it is not a replacement for professional
  emergency systems.
