# Perception Fusion Dashboard Specification

## Goal
Visualize the health of the AI's perception outcomes to quickly identify if Alan is "hearing" correctly or if calls are failing due to transport/environment issues rather than conversational logic.

## Data Sources
* **Table:** `calls`
* **Column:** `perception_vector` (JSON)
* **Column:** `final_outcome` (Text)
* **Column:** `inbound_metrics` (JSON)

## Dashboard Layout

### 1. Perception Health Overview (Top Row Tiles)
* **Start Rate:** % of calls with `perception_vector.health != 'critical'`
* **Dead Air Rate:** % of calls where `perception_vector.mode == 'dead_air'`
* **Connection Loss Rate:** % of calls where `perception_vector.mode == 'connection_loss'`
* **Avg STT Confidence:** Average of `perception_vector.stt_confidence`

### 2. Mode Distribution (Donut Chart)
* **Dimension:** `perception_vector.mode`
* **Values:** Count of calls
* **Segments:**
    * `normal` (Green)
    * `ivr` (Blue)
    * `voicemail` (Gray)
    * `dead_air` (Red)
    * `connection_loss` (Dark Red)
    * `audio_drift` (Orange)

### 3. Perception vs Outcome (Sankey Diagram or Bar Stack)
* **Left:** Perception Mode (`normal`, `dead_air`, etc.)
* **Right:** Final Outcome (`completed`, `not_interested`, `hangup`, etc.)
* **Insight:** Does `audio_drift` lead to `hangup`? Does `dead_air` correlate with specific carriers?

### 4. Technical Health Metrics (Time Series Lines)
* **X-Axis:** Time (bucketed by hour/day)
* **Y-Axis 1:** Max Outbound TTS Drift (avg per bucket)
* **Y-Axis 2:** Max Inbound Packet Gap (avg per bucket)
* **Y-Axis 3:** Silence Duration (avg per bucket)

### 5. IVR/Voicemail Detection Accuracy (Scatter Plot)
* **X-Axis:** `perception_vector.ivr_score`
* **Y-Axis:** `perception_vector.voicemail_score`
* **Color:** `final_outcome` (e.g. was `voicemail_ivr` outcome actually detected as `voicemail` by perception?)

## Implementation Notes
* Since `perception_vector` is stored as a JSON string in SQLite, the dashboard query layer (e.g., Metabase, Tableau, or custom Streamlit) needs to parse this JSON.
* **SQL Example:**
  ```sql
  SELECT 
    json_extract(perception_vector, '$.mode') as mode,
    json_extract(perception_vector, '$.health') as health,
    count(*) as count
  FROM calls
  GROUP BY 1, 2
  ```
