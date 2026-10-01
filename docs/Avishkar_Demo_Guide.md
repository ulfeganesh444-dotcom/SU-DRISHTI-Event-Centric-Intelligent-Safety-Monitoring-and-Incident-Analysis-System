# SU-DRISHTI — Avishkar Demo & Presentation Guide (2-Day Final)

## One-line project statement
> SU-DRISHTI is a context-aware intelligent safety prototype that turns passive
> camera feeds into verified, risk-prioritized incidents with evidence —
> because detection alone is not incident detection.

Say this on slide 1 and in the demo intro. It frames everything.

## What changed in this upgrade (say this to judges)
1. **Incident Verification Engine** (`src/incident_engine.py`) —
   SUSPECTED → VERIFYING → CONFIRMED over consecutive frames. One-frame
   flickers never become events.
2. **Duplicate prevention fixed** — 30-frame demo video now yields 2 events
   (was: triple-logging per person + 5 s person spam = hundreds of screenshots).
   Person cooldown is now 30 s; one event max per track per frame.
3. **Risk engine** — LOW / MEDIUM / HIGH / CRITICAL from confidence +
   persistence + zone + time + multi-detection, with reasons stored per event.
4. **Context awareness** — RESTRICTED vs MONITORED zone + night hours (22:00–06:00).
5. **Database extended without breaking** — new columns `risk_level`,
   `event_status`, `zone`, `duration_sec`; old `severity`/`status` kept and mirrored.
6. **Dashboard redesigned** — light, professional research style; status banner,
   4 KPIs, recent-incidents table, analytics (type / risk / time / zone /
   confirmed-vs-suspected), evidence gallery with operator response.

## 10-step live demo (reliable, ~4 minutes)
1. `python -m src.main --source videos/demo_intrusion.mp4 --no-gui --max-frames 200`
   — point at console: "Verification engine: SUSPECTED → VERIFYING → CONFIRMED".
2. Show console line: `intrusion ... Risk: CRITICAL | Status: CONFIRMED |
   Zone: RESTRICTED` — read the risk/zone aloud.
3. Show console line: `person ... Risk: LOW ... Zone: MONITORED` — contrast.
4. `Mission report: 30 frames → 2 incidents` — "Detection ≠ Event."
5. Open dashboard: `streamlit run Dashboard/app.py` → Current Safety Status banner.
6. Point at KPIs: Total / Confirmed / High-Risk / Critical.
7. Recent Incidents table: Time | Event | Location | Confidence | Risk | Verification.
8. Analytics: events by type, by risk, over time, by zone, confirmed vs suspected.
9. Evidence: open incident #9 screenshot — "Why this alert? Verified + risk + evidence."
10. Closing line: "Prototype for assisted monitoring, not a replacement for
    professional emergency systems."

## If webcam fails in the hall (backup plan)
- Never depend on the hall webcam. Pre-record: run the command in step 1 once
  in the morning so the DB has fresh rows, then present dashboard-only if needed.
- Keep `videos/demo_person.mp4` as second demo file.

## Honest limitations slide (judges respect this)
- Fall = bounding-box kinematics prototype, not medical validation.
- Fire chromatic mode = candidate detector; custom weights optional (`models/fire_yolov8n.pt`).
- Single-camera laptop prototype; no tracking across cameras; night logic is clock-based.
- Risk scores are project-defined priorities, not predictions.

## Future scope (1 slide, no overclaim)
Multi-camera handoff, pose-estimation fall validation, on-device alert buzzer,
opt-in mobile notification, longitudinal false-alarm study.

## Test checklist (all passing 2026-09-26)
| # | Test | Command | Pass condition |
|---|------|---------|----------------|
| 1 | DB init + migration | `python -m src.database` | prints OK; 13 columns in events |
| 2 | Verification lifecycle | `python tests/test_incident_engine.py` | SUSPECTED→VERIFYING→CONFIRMED |
| 3 | Duplicate prevention | same file | 5 repeats in cooldown → no alert |
| 4 | Risk tiers | same file | LOW / HIGH / CRITICAL asserted |
| 5 | Legacy filter | `python tests/test_event_filter.py` | all PASS |
| 6 | Logger + screenshot | `python tests/test_logger_and_screenshot.py` | row matches screenshot |
| 7 | Analytics | `python -m src.analytics` | KPI summary prints |
| 8 | Dashboard compile | `python -m py_compile Dashboard/app.py` | no error |
| 9 | End-to-end video | `python -m src.main --source videos/demo_intrusion.mp4 --no-gui --max-frames 150` | 30 frames → ~2 events with Risk/Zone/Duration |
| 10 | Dashboard data | `streamlit run Dashboard/app.py` | status + KPIs + table + evidence render |

## Files changed / created
- CREATED `src/incident_engine.py` — verification + context + risk (the core upgrade)
- EDITED `src/database.py` — 4 new columns + backfill migration
- EDITED `src/event_logger.py` — new fields, severity mirrors risk_level
- EDITED `src/main.py` — engine wired in; triple-logging fixed; 1 event/track/frame
- REPLACED `Dashboard/app.py` — professional light theme per spec
- CREATED `tests/test_incident_engine.py` — 3 tests, all passing
- PRESERVED `src/event_filter.py`, detectors, screenshot, email, camera — untouched
