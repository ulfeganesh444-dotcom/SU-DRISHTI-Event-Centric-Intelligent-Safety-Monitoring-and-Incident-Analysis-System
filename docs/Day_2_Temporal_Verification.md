# SU-DRISHTI — Day 2: Temporal + Event-Level Verification

**Status: implemented and tested 2026-09-30. Numbers below are measured, not
claimed. No accuracy improvement is reported — Day 2 builds the mechanism;
Day 3 runs the experiment.**

## 1. Problem with frame-level detection
One continuous occurrence (a person in view for seconds) produces one
detection per frame. Storing per-frame rows floods the database with
near-identical records and buries real incidents (alert fatigue). The Day 1
system already debounced with time cooldowns, but a re-confirmation still
inserted a brand-new row — duration was never tracked and one event could
still become several rows.

## 2. Proposed temporal verification
`src/incident_engine.py` (already present, kept as the single temporal
authority; configurable `REQUIRED_FRAMES` per type, constructor-overridable):
SUSPECTED (1 frame) → VERIFYING (≥2) → CONFIRMED (≥N consecutive).
New: `src/incident_store.py::TemporalStore` owns grouping states
DETECTED → VERIFYING → CONFIRMED, cooldown suppression, frame-gap closure
(`close_gap_frames=45`), and reopen extension (`reopen_gap_frames=45`).

## 3. Event grouping approach
Open-incident registry keyed by (event_type, track_id). On re-confirmation of
an open key: UPDATE the row in place (`end_time`, `duration_sec` from
frames/fps, `confidence` = max) — no new row, no new screenshot. Gap longer
than 45 frames, or a new track id, opens a genuinely new incident. Evidence
is captured only at first confirmation (`capture_fn` call count == rows
created, asserted in tests).

## 4. Incident states
Implemented today: DETECTED (baseline rows only), VERIFYING, CONFIRMED.
HUMAN_REVIEW / RESOLVED deliberately NOT implemented (interfaces exist in
`src/event_model.py` for Day 3+).

## 5. Duplicate prevention
Three layers, all at event-processing level (no post-hoc deletion):
cooldown suppression inside the engine, open-row extension instead of
re-insert, frame-gap closure of stale tracks. Configurable via constructor
(`required_frames`, `cooldowns`, `reopen/close_gap_frames`, filter cooldown).

## 6. Evidence handling
Screenshot captured only on incident creation, stored as relative path in
`image_path`; extensions keep first-confirmation evidence. Existing
`screenshots/` layout and watermarking unchanged.

## 7. Baseline vs proposed architecture
- BASELINE (`mode="baseline"`): YOLO → whitelist/confidence/cooldown filter →
  immediate row (`event_status=DETECTED`, no evidence, fixed MEDIUM risk).
  The filter is intentionally kept so the arms differ by exactly one
  variable: temporal verification + grouping.
- PROPOSED (`mode="proposed"`, default): YOLO → filter → IncidentEngine →
  TemporalStore → one extended row + evidence + selective email.
- `src/main.py` (webcam) was left on its existing engine-direct path;
  routing it through the store is Day 3 work.

## 8. Tests performed
- `tests/test_incident_store.py` (6/6 pass, scripted frames, fake DB):
  1-frame noise → 0 rows; 10 persistent frames → 1 row, delay 2 frames;
  200 continuous frames → 1 row + 197 extensions, duration 20.0 s, 1 capture;
  5-frame gap → still 1 row; 190-frame gap → 2 rows; 2 tracks → 2 rows;
  baseline 5 frames → 5 DETECTED rows.
- Real clip `videos/demo_intrusion.mp4` (30 frames), both arms, full summaries
  in `docs/day2_metrics_baseline.json` / `docs/day2_metrics_proposed.json`.

## 9. Actual observations (demo_intrusion.mp4, 30 frames, 150 raw detections)
| metric | baseline | proposed |
|---|---|---|
| rows created | 2 | 2 |
| rows extended | 0 | 0 |
| suppressed repeats | 0 | 129 |
| candidates / dismissed | 0 / 0 | 5 / 3 |
| confirm delay median (frames) | 0 | 4 |
| critical incidents | 0 | 1 (intrusion, RESTRICTED) |
| evidence files | 0 | 2 |
| processing (s) | 3.8 | 2.0 |
Read honestly: on this 3-second clip both arms store 2 rows (the filter
cooldown already suppresses most frames, and the clip is shorter than any
re-confirmation cooldown, so the extension path never fires here — it is
covered by the 200-frame synthetic test instead). Proposed additionally
yields verification states, risk, zone, evidence, and email gating. Email was
attempted once and reported `failed/not configured` (no SMTP credentials in
env) — simulation path works; real delivery untested.

## 10. Limitations
- Extension/closure windows are frame counts tuned by reasoning, not measured.
- Duration uses video fps; webcam fps fallback (30) is approximate.
- `main.py` webcam path not yet routed through the store.
- One fixed zone polygon; single-camera; no crossing-track merges.
- No HUMAN_REVIEW routing yet; uncertain cases are auto-dismissed, not queued.

## 11. Day 3 requirements
- Longer multi-event clip (or staged webcam session) that outlasts the
  15 s intrusion cooldown, to exercise extension on real video.
- Hand-labelled incident intervals for the clip(s); then report raw counts:
  incidents reported, rows per true incident, false alarms, misses, median
  confirm delay, operator actions — baseline vs proposed.
- Route `main.py` through `TemporalStore`; add `end_time` to dashboard
  evidence view; calibrate the Day-1 review band or drop it.
