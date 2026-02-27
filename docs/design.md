# Design Notes — Real-Time Traffic Monitoring Pipeline

## 1. Requirements summary
- Preprocess streams into 2-minute clips
- Track vehicles and estimate speed per lane/direction
- Compute interval-based metrics (e.g., per 5 minutes)
- Trigger alerts for overspeed events
- Support multiple cameras / lanes / directions

## 2. Architecture (high level)
- Ingestion component:
- Preprocessing component:
- Analytics component:
- Storage component:
- Alerting component:

## 3. Data model (outputs)
Describe what gets stored:
- clip metadata
- per-vehicle records (timestamp, lane, speed)
- aggregated metrics per time window
- alert events

## 4. Operational considerations
- scaling
- cost considerations
- failure modes / retries
- latency vs accuracy tradeoffs

## 5. What I contributed
- (fill in later)
