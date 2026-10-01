# Project Objectives: SU-DRISHTI

## Primary Objectives
1. **Autonomous Visual Surveillance**: Develop an automated computer-vision pipeline capable of ingesting video from both live webcam streams and pre-recorded video benchmarks.
2. **Real-Time Object & Entity Detection**: Integrate Ultralytics YOLOv8n to identify persons and safety-critical objects with confidence metrics at interactive frame rates (>=12 FPS on commodity CPU hardware).
3. **Multi-Modal Incident Detection**:
   - Implement kinematic aspect-ratio dynamics ($H/W$ inversion and ground proximity) for accidental fall detection.
   - Implement configurable virtual polygon tripwires for restricted perimeter intrusion detection.
   - Design a hybrid chromatic and custom-weights architecture for fire/flame identification.
4. **Intelligent Event Debouncing**: Implement a stateful Event Cooldown engine to eliminate duplicate event logging and database flooding during continuous target presence.
5. **Automated Evidence Capture & Chain of Custody**: Capture watermarked forensic screenshot frames with embedded timestamps and confidence headers whenever a validated incident occurs.
6. **Structured Incident Persistence**: Design and maintain a single, normalized SQLite database schema capturing incident metadata, timestamps, risk classification, and file-based evidence pointers.
7. **Interactive Command Center**: Build a responsive Streamlit dashboard providing real-time telemetry, KPI metrics, forensic evidence inspection, and temporal analytics.
8. **Emergency Dispatch Simulation**: Provide an extensible alert dispatcher capable of simulated logging and live SMTP email notifications with evidence attachments.
9. **Avishkar National Competition Demonstration**: Deliver a 100% stable, booth-proof working prototype that can effortlessly alternate between live camera feeds and pre-recorded benchmarks.

## Secondary Objectives
- Maintain clean, project-relative Python code adhering strictly to modern software engineering standards.
- Provide comprehensive automated test suites covering every architectural module.
- Eliminate dependency on costly proprietary cloud surveillance platforms through local, privacy-preserving computation.
