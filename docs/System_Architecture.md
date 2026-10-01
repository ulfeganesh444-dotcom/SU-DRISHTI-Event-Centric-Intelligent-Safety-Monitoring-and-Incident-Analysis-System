# System Architecture: SU-DRISHTI

## 1. Architectural Overview
SU-DRISHTI is engineered around a modular, decoupled pipeline where data flows unidirectionally from acquisition through deep learning, semantic filtering, evidence persistence, and presentation.

```
+-------------------------------------------------------------+
|                     1. INGESTION LAYER                      |
|           cv2.VideoCapture (Webcam Index / Video File)      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     2. INFERENCE LAYER                      |
|         Ultralytics YOLOv8n (Bounding Boxes, Conf, Classes) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 3. SAFETY ALGORITHM LAYER                   |
|  - FallDetector: Aspect-Ratio Inversion (H/W < 0.85)        |
|  - IntrusionDetector: Point-in-Polygon (Tripwire Boundary)  |
|  - FireDetector: Chromatic HSV/YCbCr & Custom Model Fallback|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                  4. EVENT FILTER & DEBOUNCE                 |
|  - Object Whitelist & Confidence Gate                       |
|  - Stateful Cooldown Timer (5s Default / 3s Critical)       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              5. FORENSIC EVIDENCE & PERSISTENCE             |
|  - Screenshot Watermarking Engine (screenshots/*.jpg)       |
|  - SQLite Event Logger (Dashboard/sentinel_ai.db)           |
+-------------------------------------------------------------+
                              |
               +--------------+--------------+
               |                             |
               v                             v
+-----------------------------+ +-----------------------------+
|    6. TELEMETRY & REPORT    | |     7. EMERGENCY DISPATCH   |
| Streamlit Command Center    | | SMTP Email Dispatcher       |
| (Dashboard/app.py)          | | (Visual / Audio Siren)      |
+-----------------------------+ +-----------------------------+
```

## 2. Component Specifications

### 2.1 Video Stream Ingestion (`src/camera.py`)
- Provides unified capture abstraction wrapping `cv2.VideoCapture`.
- Auto-detects numeric string indices (e.g. `"0"`) for webcams vs relative file paths for stored footage.
- Gracefully handles end-of-stream signals without pipeline panics.

### 2.2 Deep Learning Detection Engine (`src/detection/person_detection.py`)
- Model: Ultralytics YOLOv8 nano (`models/yolov8n.pt`).
- Parameters: 3.2M weights, 8.7 GFLOPs, optimized for real-time edge CPU inference.
- Output: Structured detection tuples `(x1, y1, x2, y2, confidence, class_name)`.

### 2.3 Kinematic Fall Detection Algorithm (`src/detection/fall_detection.py`)
- **Mathematical Principle**: Standing bipedal humans exhibit vertical aspect ratios $R = \frac{H}{W} \in [1.2, 3.5]$. During an unrecovered fall, the aspect ratio inverts to $R < 0.85$ while the lower bounding coordinate $y_2$ approaches the ground plane ($y_2 > 0.50 \times H_{\text{frame}}$).
- **Temporal Debounce**: Requires the fallen posture to persist across $K \ge 4$ consecutive frames to reject momentary floor interactions or dropped objects.

### 2.4 Virtual Perimeter Tripwire (`src/detection/intrusion_detection.py`)
- Implements arbitrary convex or non-convex polygonal regions of interest defined by normalized coordinates $[(x_i, y_i)]$.
- Evaluates the human target's base footprint $((x_1+x_2)/2, y_2)$ using Ray Casting via `cv2.pointPolygonTest`.

### 2.5 Event Debounce Filter (`src/event_filter.py`)
- Maintains an in-memory chronological state table `_last_logged_time: Dict[str, float]`.
- Enforces minimum confidence thresholding and prevents multi-frame event flooding.

### 2.6 Forensic Evidence & Persistence (`src/alerts/screenshot.py`, `src/event_logger.py`, `src/database.py`)
- Generates watermarked JPG files with forensic audit banners.
- Inserts indexed records into `Dashboard/sentinel_ai.db`.
