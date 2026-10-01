# Project Roadmap: SU-DRISHTI

## Phase 1: MVP Core Pipeline (Target: September 2026) — [COMPLETED]
- [x] Project architecture and dependency scaffolding.
- [x] SQLite database schema design and project-relative persistence handler (`Dashboard/sentinel_ai.db`).
- [x] Event logger with incident metadata persistence.
- [x] Forensic evidence capture engine with timestamp/confidence watermarking (`screenshots/`).
- [x] Smart Event Filter with Cooldown debounce mechanism (5s default / 3s critical).
- [x] YOLOv8n object and person detection integration (`models/yolov8n.pt`).
- [x] Virtual perimeter tripwire intrusion detection.
- [x] Kinematic aspect-ratio fall detection heuristic.
- [x] Streamlit Command Center dashboard (`Dashboard/app.py`).
- [x] Automated unit and integration test suite (`tests/run_all_tests.py`).

## Phase 2: Avishkar 2027 Demonstration & Refinement — [IN PROGRESS]
- [x] Benchmark video demo modes (`videos/demo_intrusion.mp4`, `videos/demo_person.mp4`).
- [ ] Physical webcam calibration and testing at presentation booth.
- [ ] SMTP email live credentials integration (optional live dispatch).
- [ ] UI refinements: dark-mode styling, telemetry graphs, and incident audio siren alerts.

## Phase 3: Future Research Extensions (Post-Avishkar Scope) — [PLANNED]
- [ ] Fine-tuned YOLOv8 custom weights for fire and dense smoke detection (`fire_yolov8n.pt`).
- [ ] Multi-camera RTSP concurrent stream management.
- [ ] 3D pose estimation fusion for complex fall kinetics.
- [ ] Edge IoT hardware integration (Raspberry Pi 5 / NVIDIA Jetson Orin Nano).
- [ ] End-to-end encrypted cloud storage sync for evidence preservation.
