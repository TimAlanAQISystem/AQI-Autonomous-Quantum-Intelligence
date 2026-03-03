"""
AQI Voice CSV Trajectory Exporter (v1.0)
----------------------------------------

Exports per-turn trajectory data from the voice regression harness
into CSV files for visualization and governance review.
"""

from __future__ import annotations

import csv
import os
from typing import List, Dict, Any, Optional


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def export_voice_trajectory_to_csv(
    scenario_name: str,
    trajectory: List[Dict[str, Any]],
    output_dir: str = "voice_regression_csv",
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    stance_keys = set()
    for turn in trajectory:
        stance = turn.get("stance")
        if isinstance(stance, dict):
            stance_keys.update(stance.keys())
    stance_keys = sorted(list(stance_keys))

    csv_path = os.path.join(output_dir, f"{scenario_name}_trajectory.csv")

    header = ["turn", "transcript", "content", "energy"]
    for key in stance_keys:
        header.append(f"stance_{key}")
    header.append("delta_energy")
    for key in stance_keys:
        header.append(f"delta_stance_{key}")

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)

        prev_energy: Optional[float] = None
        prev_stance: Optional[Dict[str, float]] = None

        for idx, turn in enumerate(trajectory):
            transcript = turn.get("transcript", "")
            content = turn.get("content", "")
            energy = _safe_float(turn.get("energy"))
            stance = turn.get("stance") if isinstance(turn.get("stance"), dict) else {}

            delta_energy = None
            if prev_energy is not None and energy is not None:
                delta_energy = energy - prev_energy

            delta_stances: Dict[str, Optional[float]] = {}
            for key in stance_keys:
                prev_val = prev_stance.get(key) if prev_stance else None
                curr_val = stance.get(key)
                if prev_val is not None and curr_val is not None:
                    delta_stances[key] = curr_val - prev_val
                else:
                    delta_stances[key] = None

            row = [idx, transcript, content, energy]
            for key in stance_keys:
                row.append(stance.get(key))
            row.append(delta_energy)
            for key in stance_keys:
                row.append(delta_stances[key])

            writer.writerow(row)

            prev_energy = energy
            prev_stance = stance

    return csv_path
