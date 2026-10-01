# Project Proposal: SU-DRISHTI

## 1. Project Identification
- **Project Title**: SU-DRISHTI — Intelligent Home Safety & Incident Detection Platform
- **Academic Degree**: B.Sc. Computer Science (Final-Year Project)
- **Competition Target**: Avishkar 2027 (National Innovation Competition)
- **Primary Domain**: Computer Vision, Artificial Intelligence, Edge Computing, Safety Systems

## 2. Project Motivation
Conventional video surveillance relies heavily on human attention to identify critical events. Human vigilance inevitably degrades over extended monitoring shifts. By infusing computer vision directly at the camera edge, SU-DRISHTI transforms cameras from passive recorders into active, vigilant safety sentinels.

## 3. Scope of Work
- Ingest real-time camera streams (webcam/video).
- Perform high-speed multi-class object detection using YOLOv8n.
- Analyze human kinematic dynamics for accidental fall detection.
- Enforce spatial perimeter security using virtual polygonal tripwires.
- Prevent duplicate data explosions using stateful debounce cooldown filters.
- Capture timestamped, watermarked visual evidence frames.
- Persist structured incident records in a local SQLite database.
- Present a real-time Command Center with interactive filtering and forensic inspection via Streamlit.
- Support simulated and live emergency dispatch (email/siren).

## 4. Key Contributions for Avishkar Evaluators
1. **End-to-End System Integration**: Bridging hardware ingestion, deep learning, algorithmic heuristics, relational persistence, and interactive user interfaces into a unified workflow.
2. **Debounce Innovation**: Eliminating the ubiquitous "frame-spam" flaw present in naive academic demos.
3. **Scientific Fall Detection**: Defensible, lightweight aspect-ratio and ground-plane kinematic formulation that operates on low-cost hardware.
4. **Privacy-Preserving Edge Architecture**: 100% on-premise execution with zero cloud subscription lock-in.
