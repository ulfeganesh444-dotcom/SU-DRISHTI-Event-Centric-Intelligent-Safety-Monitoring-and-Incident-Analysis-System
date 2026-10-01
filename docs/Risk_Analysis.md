# Risk Analysis & Ethical Limitations: SU-DRISHTI

## 1. Technical Limitations (Academic Honesty)
In accordance with rigorous academic and scientific standards for Avishkar 2027, the limitations of SU-DRISHTI are explicitly acknowledged:

1. **Illumination Sensitivity**: Computer vision models exhibit performance degradation under severe low-light (<10 lux) or high-glare conditions without infrared (IR) illumination.
2. **Partial Occlusion**: When a person is partially blocked by furniture, bounding boxes may underestimate height, potentially influencing aspect-ratio fall calculations.
3. **Model Accuracy vs Latency Tradeoff**: The YOLOv8n (nano) architecture prioritizes inference speed (real-time CPU execution) over the slightly higher mAP of heavier models (YOLOv8x).
4. **Hardware Variability**: Webcams lacking auto-focus or running at low frame rates (<15 FPS) may experience motion blur during rapid kinematic transitions.
5. **Prototype Disclaimer**: SU-DRISHTI is an academic engineering prototype and must not be marketed or deployed as a certified industrial life-safety system.

## 2. Risk Matrix & Mitigation Strategies

| Risk Description | Severity | Likelihood | Mitigation Strategy Implemented |
| :--- | :--- | :--- | :--- |
| **Database Flooding** (Redundant frame writes) | High | High | Implemented stateful Event Debounce Cooldown (5s/3s) in `src/event_filter.py`. |
| **False Alarms on Pets/Robovac** | Medium | Medium | Strict semantic whitelisting and minimum confidence thresholds. |
| **Presentation Hardware Failure at Competition** | High | Medium | Provided dual input modes: live webcam (`--source 0`) and benchmark test videos (`--source videos/demo_intrusion.mp4`). |
| **Corrupt Image References** | Medium | Low | Project-relative path normalization ensuring cross-platform path integrity. |
| **Privacy Concerns** | High | Medium | All inference runs locally on the host machine; no video frames are transmitted to external cloud servers. |
