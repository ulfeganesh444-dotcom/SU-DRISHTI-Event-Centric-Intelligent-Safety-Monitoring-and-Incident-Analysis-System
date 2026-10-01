# Literature Survey & Theoretical Background: SU-DRISHTI

## 1. Evolution of Automated Visual Surveillance
Automated surveillance systems have evolved from early background-subtraction methods (such as Gaussian Mixture Models - GMM) to deep Convolutional Neural Networks (CNNs) and transformer-based architectures.

- **Stauffer & Grimson (1999)** demonstrated adaptive background mixture models for real-time tracking. While computationally light, GMMs suffer from high sensitivity to illumination variations, shadows, and dynamic backgrounds.
- **Redmon et al. (2016)** introduced YOLO (You Only Look Once), reframing object detection as a unified regression problem. Unlike two-stage detectors (Faster R-CNN), YOLO evaluates the full frame in a single forward pass.
- **Jocher et al. (2023)** introduced YOLOv8 by Ultralytics, featuring an anchor-free split head with decoupled classification and bounding-box regression, achieving superior Mean Average Precision (mAP) with reduced computational complexity.

## 2. Fall Detection Methodologies in Computer Vision
Existing literature categorizes visual fall detection into three paradigms:
1. **Wearable Sensor Fusion**: Accelerometers and gyroscopes worn on the body. While accurate, wearable compliance among elderly demographics is notoriously low (<40% compliance rate after 3 months).
2. **Pose Estimation (Keypoint Graph Networks)**: Models like OpenPose or YOLOv8-pose track 17 human joints. However, high computational overhead restricts multi-stream edge deployment without discrete GPUs.
3. **Kinematic Bounding-Box Heuristics (SU-DRISHTI Approach)**: Analyzing aspect-ratio ($R = H/W$) transitions, centroid velocity ($\Delta y / \Delta t$), and floor proximity. Forughi et al. (2008) and Mirmahboub et al. (2013) demonstrated that aspect-ratio dynamics combined with temporal persistence yield over 90% sensitivity on standard fall benchmarks while operating at over 10x the frame rate of full pose estimation networks.

## 3. Perimeter Intrusion & Spatial Geofencing
Traditional infrared beam tripwires lack semantic context (triggering false alarms on pets, leaves, or weather). Combining semantic classification (filtering strictly for class `person`) with polygonal Ray Casting (`cv2.pointPolygonTest`) enables zero-false-alarm virtual tripwires without auxiliary physical sensors.
