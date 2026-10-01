# Problem Statement: SU-DRISHTI

## 1. Context & Background
Video surveillance infrastructure has experienced exponential adoption globally across private residences, assisted-living facilities, and commercial properties. However, modern surveillance systems remain fundamentally passive: they record continuous video streams to digital video recorders (DVRs) or cloud storage, relying on human operators to observe anomalies or conduct post-incident forensic reviews.

## 2. The Core Problem
1. **Human Fatigue & Cognitive Overload**: Research in vigilance and human perception shows that human attention degrades by over 45% after only 20 minutes of continuous monitor observation, leading to missed critical safety incidents.
2. **Delayed Response in Critical Emergencies**: In home safety scenarios—such as elderly slip-and-fall accidents, unauthorized physical intrusions, or fire outbreaks—reaction time directly correlates with mortality and property damage.
3. **Data Explosion vs Actionable Insight**: Traditional systems generate hundreds of gigabytes of unstructured video without semantic labeling. Finding a specific safety incident requires hours of manual timeline scrubbing.
4. **Toy Computer Vision Pitfalls**: Generic AI demos display bounding boxes on screens but fail in practice due to database flooding (logging 30 duplicate events per second for a stationary person) and lack of forensic evidence linkages.

## 3. The SU-DRISHTI Solution
SU-DRISHTI addresses these systemic challenges by creating an autonomous, intelligent incident detection and forensic management pipeline that:
- Continuously analyzes video frames using high-speed deep learning (YOLOv8).
- Implements kinematic geometric reasoning to detect falls and spatial tripwires for perimeter breaches.
- Filters redundant detections through stateful cooldown debouncing.
- Captures watermarked photographic evidence with timestamp audit trails.
- Persists structured incident records in a lightweight local SQLite database.
- Provides a centralized command-and-control Streamlit dashboard for real-time monitoring and analytics.
