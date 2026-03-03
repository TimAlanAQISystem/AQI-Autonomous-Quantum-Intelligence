# Behavioral Fusion Dashboard Specification

## Goal
Visualize the "Behavioral State" of the AI to understand *how* it is navigating conversations, not just *what* it is achieving. This fuses fluidity, emotional trajectory, and objection physics into a single view.

## Data Sources
* **Table:** `calls`
* **Column:** `behavioral_vector` (JSON)
* **Column:** `perception_vector` (JSON)
* **Column:** `final_outcome` (Text)

## Dashboard Layout

### 1. Behavioral Health Overview (Top Row Tiles)
* **Optimal Rate:** % of calls with `behavioral_vector.health == 'optimal'`
* **Collapse Rate:** % of calls where `behavioral_vector.mode == 'collapsed'`
* **High Friction Rate:** % of calls where `behavioral_vector.mode == 'high_friction'`
* **Avg Turn Count:** Average of `behavioral_vector.turn_count`

### 2. Behavioral Mode Distribution (Donut Chart)
* **Dimension:** `behavioral_vector.mode`
* **Values:** Count of calls
* **Segments:**
    * `normal` (Green)
    * `recovering` (Blue)
    * `high_friction` (Orange)
    * `stalled` (Yellow)
    * `collapsed` (Red)

### 3. Trajectory vs Outcome (Scatter Plot)
* **X-Axis:** `behavioral_vector.trajectory_velocity` (Speed of progress)
* **Y-Axis:** `behavioral_vector.trajectory_drift` (Emotional alignment)
* **Color:** `final_outcome`
* **Insight:** Do high-velocity calls actually close? Or do they rush past objections?

### 4. Friction Analysis (Bar Chart)
* **X-Axis:** `behavioral_vector.objection_count` (0, 1, 2, 3, 4+)
* **Y-Axis:** Conversion Rate (Outcome = 'scheduled' / 'interested')
* **Insight:** How many objections can we handle before the deal collapses?

### 5. Fluidic State Transition Heatmap
* **Rows:** `behavioral_vector.fluidic_state` (End state)
* **Columns:** `behavioral_vector.health`
* **Insight:** Are we collapsing in `NEGOTIATION` or `OPENING`?

## Implementation Notes
* Since `behavioral_vector` is stored as a JSON string, dashboard queries must parse it.
* **SQL Example:**
  ```sql
  SELECT 
    json_extract(behavioral_vector, '$.mode') as mode,
    json_extract(behavioral_vector, '$.health') as health,
    avg(json_extract(behavioral_vector, '$.trajectory_velocity')) as avg_velocity
  FROM calls
  WHERE behavioral_vector IS NOT NULL
  GROUP BY 1, 2
  ```
