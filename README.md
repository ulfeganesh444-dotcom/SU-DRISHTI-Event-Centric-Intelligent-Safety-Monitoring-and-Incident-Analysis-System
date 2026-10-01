# SU-DRISHTI — Intelligent Home Safety & Incident Detection Platform

> **See Beyond Vision, Protect Beyond Detection.**

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/Ultralytics-YOLOv8n-green.svg)](https://github.com/ultralytics/ultralytics)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/SQLite-Structured%20Events-lightgrey.svg)](https://www.sqlite.org/)
[![Project](https://img.shields.io/badge/Avishkar-2027%20National%20Level-orange.svg)]()

> **Final-Year B.Sc. Computer Science Project & Avishkar 2027 Innovation Submission**

---

## 📌 Executive Summary

Traditional CCTV surveillance systems record petabytes of passive footage but require continuous human fatigue-prone monitoring. Important incidents—such as accidental falls of elderly residents, unauthorized perimeter intrusions, and safety hazards—frequently go unnoticed until it is too late.

**SU-DRISHTI** transforms passive camera feeds into an **active, intelligent safety platform**. Using real-time computer vision (Ultralytics YOLOv8), algorithmic kinematic posture analysis, virtual perimeter tripwires, intelligent cooldown debouncing, and automated forensic evidence capture, SU-DRISHTI extracts structured safety incidents into a local SQLite database and delivers real-time telemetry through a Streamlit Command Center.

---

## 🏗️ System Architecture

```
                  SU-DRISHTI PIPELINE
                         │
                         ▼
              Camera / Benchmark Video
                         │
                         ▼
             YOLOv8n Object Detection
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
Human Kinematic Analysis         Virtual Perimeter ROI
(Height/Width Ratio Dynamics)   (Point-in-Polygon Tripwire)
         │                               │
         └───────────────┬───────────────┘
                         │
                         ▼
            Smart Event Cooldown Filter
         (Debounce Duplicate Frame Floods)
                         │
                         ▼
             Forensic Evidence Capture
       (Timestamped & Watermarked Image)
                         │
                         ▼
                Event Persistence
             (Dashboard/sentinel_ai.db)
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
Streamlit Command Center         Emergency Dispatch
(Live Incidents & Evidence)     (Email & Visual Siren)
```

---

## 🔬 Core Innovations & Methodologies

1. **Intelligent Event Cooldown (Debounce Filter)**:
   - Prevents database flooding and redundant disk writes. Naive object detection logs 30 events per second for a standing person. SU-DRISHTI implements stateful cooldowns (e.g., 5s default, 3s critical) to ensure unique, actionable incidents.
2. **Kinematic Fall Detection**:
   - Evaluates bounding-box aspect ratio ($R = H / W$). Standing postures exhibit $R > 1.25$, whereas fallen postures invert to $R < 0.85$ near the floor plane ($y_2 > 0.5 \times H_{\text{frame}}$) persisting over consecutive frames.
3. **Virtual Perimeter Tripwire (Intrusion Detection)**:
   - Defines configurable polygonal Regions of Interest (ROI). Evaluates target base coordinates using `cv2.pointPolygonTest` to detect unauthorized physical breaches.
4. **Forensic Evidence Watermarking**:
   - Automatically saves forensic frames with embedded metadata headers (timestamp, detection confidence, incident classification) to `screenshots/`.
5. **Booth-Proof Dual Input**:
   - Seamlessly switches between live webcam devices (`--source 0`) and benchmark test videos (`--source videos/demo.mp4`) for resilient competition presentations.

---

## 📁 Clean Directory Layout

```text
Avishkar2027/
│
├── models/                     # Deep learning weights (yolov8n.pt)
│   └── yolov8n.pt
│
├── Dashboard/                  # Interactive Command Center
│   ├── app.py                  # Streamlit dashboard application
│   └── sentinel_ai.db          # Central SQLite incident database
│
├── screenshots/                # Watermarked forensic evidence images
├── videos/                     # Demo and test video streams
├── logs/                       # Application logs
├── docs/                       # Research documentation & Avishkar reports
├── tests/                      # Unit and integration test suites
│
├── src/                        # Clean modular source code
│   ├── __init__.py
│   ├── main.py                 # Core application pipeline coordinator
│   ├── database.py             # SQLite connection & schema management
│   ├── event_logger.py         # Incident persistence handler
│   ├── event_filter.py         # Debounce cooldown & whitelisting engine
│   ├── camera.py               # Unified video stream capture abstraction
│   ├── analytics.py            # Aggregate telemetry & KPI reporting
│   │
│   ├── detection/              # Modular detection engines
│   │   ├── __init__.py
│   │   ├── person_detection.py # YOLOv8 person & object detector
│   │   ├── fall_detection.py   # Kinematic aspect-ratio fall engine
│   │   ├── intrusion_detection.py # Polygonal ROI tripwire perimeter
│   │   ├── fire_detection.py   # Dual-mode chromatic & custom fire engine
│   │   └── video_detection.py  # Standalone video file processor
│   │
│   └── alerts/                 # Incident dispatch mechanisms
│       ├── __init__.py
│       ├── screenshot.py       # Evidence capture & watermarking
│       └── email_alert.py      # SMTP emergency alert dispatcher
│
├── requirements.txt            # Dependency specifications
└── README.md                   # Project documentation
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites & Installation
Ensure Python 3.10+ is installed:
```powershell
pip install -r requirements.txt
```

### 2. Verify System Modules
Execute the automated test suite:
```powershell
python tests/test_env.py
python tests/test_database.py
python tests/test_logger_and_screenshot.py
python tests/test_event_filter.py
python tests/test_person_detection.py
python tests/test_safety_modules.py
```

### 3. Launch SU-DRISHTI Monitoring
Run from the project root:
```powershell
# Live Webcam Monitoring
python -m src.main

# Or Run on Benchmark Video
python -m src.main --source videos/demo_intrusion.mp4
```

### 4. Launch Streamlit Command Center
In a separate terminal, launch the dashboard:
```powershell
streamlit run Dashboard/app.py
```
Open your browser at: `http://localhost:8501`

---

## 📊 Database Schema (`Dashboard/sentinel_ai.db`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key (Autoincrement) |
| `object_name` | TEXT | Incident type (`person`, `fall`, `intrusion`, etc.) |
| `confidence` | REAL | Model prediction confidence score (0.00 – 1.00) |
| `source` | TEXT | Video capture source identifier |
| `event_time` | TEXT | Forensic timestamp (`YYYY-MM-DD HH:MM:SS`) |
| `image_path` | TEXT | Relative path to evidence image in `screenshots/` |
| `severity` | TEXT | Risk classification (`LOW`, `MEDIUM`, `CRITICAL`) |

---

## 🛡️ Presentation & Demo Walkthrough for Avishkar

1. **Problem Statement**: Emphasize that traditional CCTV is passive and prone to human oversight.
2. **Live Feed**: Run `python -m src.main` to demonstrate real-time person tracking and cooldown debouncing.
3. **Trigger Incident**: Show the live perimeter tripwire in action by stepping into the restricted zone or playing `videos/demo_intrusion.mp4`.
4. **Inspect Evidence**: Switch to the Streamlit Dashboard (`Dashboard/app.py`), select the newly recorded incident, and display the watermarked forensic screenshot with confidence and timestamp.
5. **Research Rigor**: Walk through the kinematic aspect-ratio equations for fall detection and explain how cooldown debouncing protects storage integrity.
