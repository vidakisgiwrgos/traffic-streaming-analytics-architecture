# Real-Time Traffic Monitoring — Distributed Cloud Pipeline (Azure)

A distributed cloud-based pipeline designed for real-time traffic monitoring using streamed video data, preprocessing, analytics, and alerting.

This repository documents the system architecture, design decisions, and deliverables (portfolio-style case study).  
*Code is not included (lost after course completion); the repo focuses on architecture and system design.*

---

## Goals

- Process live traffic camera streams
- Preprocess video into short clips (2-minute segments)
- Run video analytics (vehicle tracking / speed estimation)
- Store results and compute per-interval statistics (e.g., every 5 minutes)
- Trigger real-time alerts (e.g., overspeed events)

---

## System Overview

High-level pipeline:

1. **Input Streams**: traffic camera streams (2 directions, multiple lanes)
2. **Preprocessing**: clip generation (2-minute clips), naming & organization in storage
3. **Video Analytics**: vehicle tracking and speed computation
4. **Storage / Analytics Layer**: aggregated outputs and metrics
5. **Alerts**: real-time notifications for rule violations (e.g., speed limit)

---

## Video Analytics Implementation

The video analytics component includes a YOLOv8 + DeepSORT pipeline for:

- Vehicle detection
- Multi-object tracking
- Speed estimation per vehicle
- Lane-based analysis

Implementation available under:
`analytics/video_tracking/YOLOv8_DeepSORT_Tracking_SpeedEstimation.ipynb`

---

## Deliverables Covered

- Data pipeline design (batch + streaming components)
- Clip storage conventions and preprocessing logic
- Metric computation (counts, averages, peaks)
- Alerting logic for overspeed events
- Discussion of scalability and operational constraints

---

## Repository Structure

- `docs/` — Design notes, assumptions, decisions
- `diagrams/` — Architecture diagrams
- `report/` — Report / deliverables (if available)
- `assets/` — Images used in documentation

---

## Tech Stack (planned / used)

- Azure (storage + compute + streaming components)
- Python (analytics scripting)
- Computer Vision module (vehicle tracking / speed estimation)

---

## Status

Academic project — completed.
