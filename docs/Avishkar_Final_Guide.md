# SU-DRISHTI — Final Guide: Test, Run & Present (Avishkar 2027)

> One-line project statement: **SU-DRISHTI is a context-aware intelligent
> safety prototype that turns passive camera feeds into verified,
> risk-prioritized incidents with evidence — because detection alone is not
> incident detection.**

## 1. System at a glance

```
Camera / Video
      -> Detection Layer (YOLOv8n + ByteTrack, fall kinematics, zone tripwire, fire chromatic)
      -> Event Filtering (whitelist + confidence gate)
      -> Temporal Verification (SUSPECTED -> VERIFYING -> CONFIRMED)
      -> Context Engine (EVENT + TIME + ZONE + PERSISTENCE)
      -> Risk Engine (LOW / MEDIUM / HIGH / CRITICAL, with reasons)
      -> Incident Confirmation (cooldown debounce: Detection != Event)
      -> Evidence Capture (watermarked screenshot)
      -> SQLite Event Store (Dashboard/sentinel_ai.db)
      -> Dashboard + Alert (Streamlit + email simulation)
```

Key rule: **an object detected in one frame is NOT an event.** Only a
detection that persists across consecutive frames (e.g. intrusion 3 frames,
fall 4, person 5, fire 6) becomes CONFIRMED, and even then a per-type
cooldown (person 30 s, intrusion/fall 15 s, fire 10 s) stops duplicate rows.

## 2. Full testing checklist (TEST 1–10)

| # | Test | Command (from project root) | INPUT | EXPECTED OUTPUT | PASS CONDITION |
|---|------|-----------------------------|-------|-----------------|----------------|
| 1 | Database init + migration | `python -m src.database` | existing/new `Dashboard/sentinel_ai.db` | `[OK] Database initialized successfully at: ...` | 13 columns in `events`: id, object_name, confidence, source, event_time, image_path, severity, status, notes, risk_level, event_status, zone, duration_sec |
| 2 | Person detection (YOLO) | `python tests/test_person_detection.py` | `videos/bus.jpg` | person boxes found, annotated output | exits without assertion error |
| 3 | Event filtering | `python tests/test_event_filter.py` | whitelist/confidence/cooldown cases | 5 × `[PASS]` lines | `EVENT FILTER TEST PASSED` |
| 4 | Duplicate prevention | `python tests/test_incident_engine.py` | same person 5× inside cooldown | `[PASS] duplicate/cooldown suppression` | repeats return `should_alert=False` |
| 5 | Incident verification | `python tests/test_incident_engine.py` | intrusion 3 consecutive frames | `[PASS] lifecycle SUSPECTED->VERIFYING->CONFIRMED` | alert only on 3rd frame |
| 6 | Risk classification | `python tests/test_incident_engine.py` | person / fall / fire+person cases | `[PASS] risk tiers LOW / HIGH / CRITICAL` | LOW≈27, HIGH≈75, CRITICAL≈100 |
| 7 | Screenshot evidence | `python tests/test_logger_and_screenshot.py` | test frame | `[PASS] Screenshot saved: screenshots/test_alert_*.jpg` | file exists on disk |
| 8 | SQLite logging | `python tests/test_logger_and_screenshot.py` | same event | `[EVENT LOGGED] ID: N ... Risk: ... Zone: ...` | DB row matches screenshot path |
| 9 | Dashboard | `python -m py_compile Dashboard/app.py` + `streamlit run Dashboard/app.py` | events in DB | compiles silent; browser shows status + KPIs + table + charts + evidence | page renders, no exception |
| 10 | End-to-end workflow | `python -m src.main --source videos/demo_intrusion.mp4 --no-gui --max-frames 150` | 30-frame demo video | `intrusion ... CRITICAL ... RESTRICTED` + `person ... LOW ... MONITORED`; `Total Incidents Logged : 2` | ≤3 events from 30 frames, each with Risk/Zone/Duration |

Run everything at once: `python tests/run_all_tests.py`

## 3. How to run (exact commands)

```powershell
cd "C:\Users\Nasscom309\Documents\Ganesh\Avishkar2027"

# A. Headless end-to-end on demo video (reliable, no webcam needed)
python -m src.main --source videos/demo_intrusion.mp4 --no-gui --max-frames 150

# B. Live webcam (needs GUI + camera)
python -m src.main --source 0

# C. Dashboard (second terminal, then open http://localhost:8501)
streamlit run Dashboard/app.py
```

## 4. 10-step live demo script (~4 minutes)

1. Start pipeline (command A above). Narrate: "Detect → Verify → Context → Risk → Confirm."
2. Console shows `intrusion ... Risk: CRITICAL | Status: CONFIRMED | Zone: RESTRICTED` — read it aloud.
3. Console shows `person ... Risk: LOW ... Zone: MONITORED` — contrast the two.
4. Mission report: `30 frames → 2 incidents` — "Detection ≠ Event."
5. Open dashboard → Current Safety Status banner.
6. KPIs: Total Events / Confirmed Incidents / High-Risk / Critical.
7. Recent Incidents table: Time | Event | Location | Confidence | Risk | Verification.
8. Analytics: by type, by risk, over time, by zone, confirmed vs suspected.
9. Evidence: open the intrusion screenshot — "Why this alert? Verified + risk + evidence."
10. Close: "Assisted-monitoring prototype, not a replacement for professional emergency systems."

Hall-webcam backup: pre-run command A in the morning so the DB is fresh;
present dashboard-only if the camera fails.

## 5. Risk logic (explainable, project-defined — not a diagnosis)

Base: person 10, intrusion 50, fall 50, fire 65, knife 80.
Modifiers: +confidence×20, +persistence (2/s, max 15), +15 restricted zone,
+10 night (22:00–06:00), +20 multiple detections together.
Bands: ≥80 CRITICAL, ≥55 HIGH, ≥30 MEDIUM, else LOW.

## 6. Files changed in this upgrade

- CREATED `src/incident_engine.py` — verification + context + risk core
- EDITED `src/database.py` — 4 columns (`risk_level, event_status, zone, duration_sec`) + backfill
- EDITED `src/event_logger.py` — new fields; `severity` mirrors `risk_level`
- EDITED `src/main.py` — engine wired in; triple-logging fixed; 1 event/track/frame
- REPLACED `Dashboard/app.py` — professional light research theme
- CREATED `tests/test_incident_engine.py` — 3 tests
- PRESERVED detectors, `event_filter.py`, screenshot, email, camera — untouched
