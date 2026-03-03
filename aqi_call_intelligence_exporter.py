"""
AQI Unified Call Intelligence Exporter (v1.0)
--------------------------------------------

Exports fused call intelligence streams from AQIEventFusionEngine as:

    - JSON (one file per call)
    - CSV (one file per call)

Includes:
    - event_type
    - speaker
    - transcript
    - sentiment
    - summary
    - action_items
    - stance
    - energy
    - drift info (if present)
"""

from __future__ import annotations
from typing import List
import json
import csv
import os

from aqi_event_fusion_layer import AQIEvent, AQIEventFusionEngine


def export_call_intelligence_json(
    fusion_engine: AQIEventFusionEngine,
    call_sid: str,
    output_dir: str = "call_intelligence_json",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    events: List[AQIEvent] = fusion_engine.get_fused_stream(call_sid)

    path = os.path.join(output_dir, f"{call_sid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            [e.__dict__ for e in events],
            f,
            ensure_ascii=False,
            indent=2,
        )
    return path


def export_call_intelligence_csv(
    fusion_engine: AQIEventFusionEngine,
    call_sid: str,
    output_dir: str = "call_intelligence_csv",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    events: List[AQIEvent] = fusion_engine.get_fused_stream(call_sid)

    path = os.path.join(output_dir, f"{call_sid}.csv")

    header = [
        "index",
        "event_type",
        "speaker",
        "transcript",
        "sentiment",
        "sentiment_score",
        "summary",
        "action_items",
        "stance",
        "energy",
        "drift",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for idx, e in enumerate(events):
            writer.writerow([
                idx,
                e.event_type,
                e.speaker,
                e.transcript,
                e.sentiment,
                e.sentiment_score,
                e.summary,
                "|".join(e.action_items or []) if e.action_items else "",
                json.dumps(e.stance) if e.stance is not None else "",
                e.energy,
                json.dumps(e.drift) if e.drift is not None else "",
            ])

    return path
