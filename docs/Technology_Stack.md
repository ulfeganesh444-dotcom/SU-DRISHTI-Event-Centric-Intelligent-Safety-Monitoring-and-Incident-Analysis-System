# Technology Stack: SU-DRISHTI

| Tier / Domain | Technology | Justification & Role in Architecture |
| :--- | :--- | :--- |
| **Core Runtime** | Python 3.14 / 3.10+ | Primary language chosen for rich scientific ecosystem, rapid prototyping, and clean cross-platform execution. |
| **Computer Vision** | OpenCV (`opencv-python 5.0.0`) | High-performance frame acquisition, image preprocessing, polygonal ray casting, visual watermarking, and HUD rendering. |
| **Object Detection** | Ultralytics YOLOv8n (`yolov8n.pt`) | State-of-the-art anchor-free real-time object detector with 3.2M parameters. Selected for high mAP and low-latency CPU inference. |
| **Kinematic Heuristics** | NumPy (`numpy 2.5.3`) | High-speed vectorized bounding box coordinate transformations, aspect-ratio dynamics, and array manipulations. |
| **Telemetry & Data** | Pandas (`pandas 3.0.5`) | Structured incident tabular data manipulation, filtering, aggregation, and time-series extraction. |
| **Database Persistence**| SQLite (`sqlite3`) | Serverless, zero-configuration relational database with ACID guarantees, perfectly suited for edge surveillance appliances. |
| **Dashboard UI** | Streamlit (`streamlit 1.63.0`) | Rapid, modern web-based Command Center providing real-time telemetry, interactive filtering, and evidence image inspection. |
| **Emergency Dispatch** | Python `smtplib` & `email.mime` | Standards-based multipart email dispatch with embedded forensic photographic evidence. |
| **Environment** | PowerShell & Python venv | Reproducible development environment on Windows 64-bit systems. |
