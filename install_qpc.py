"""
install_qpc.py

Thin shim for wiring QPC-2 into any backend without extra tooling.
- Initializes the unified engine + chamber singletons.
- Exposes route_through_qpc(input_dict) -> output_dict for drop-in calls.
- Provides a minimal __main__ smoke test.
"""
from __future__ import annotations

from typing import Any, Dict, List

from qpc2_engine import (
    UnifiedRelationalEngine,
    QPC2Chamber,
    QPC2Input,
    QPC2Output,
)

_engine = UnifiedRelationalEngine()
_chamber = QPC2Chamber(engine=_engine)


def route_through_qpc(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single message through QPC-2 and return a plain dict.

    Expected payload keys:
      - source: str
      - caller_id: str
      - raw_message: str
      - epistemic_layer: str
      - anchors: List[str]
      - prior_string_id: str ("" for new thread)
      - debug_mode: bool
    Missing optional keys fall back to safe defaults.
    """
    anchors: List[str] = payload.get("anchors") or []
    qin = QPC2Input(
        source=payload.get("source", "unknown"),
        caller_id=payload.get("caller_id", "anon"),
        raw_message=payload.get("raw_message", ""),
        epistemic_layer=payload.get("epistemic_layer", "general"),
        anchors=anchors,
        prior_string_id=payload.get("prior_string_id", ""),
        debug_mode=bool(payload.get("debug_mode", False)),
    )

    qout: QPC2Output = _chamber.handle(qin)

    return {
        "string_id": qout.string_id,
        "content": qout.content,
        "stance": qout.stance,
        "anchors": qout.anchors,
        "scores": qout.scores,
        "epistemic_layer": qout.epistemic_layer,
        "drift_flags": qout.drift_flags,
        "governance_action": qout.governance_action,
    }


if __name__ == "__main__":
    demo_payload = {
        "source": "console",
        "caller_id": "timmyj",
        "raw_message": "Protect the boundary. Do not soften. Remember what happened.",
        "epistemic_layer": "ethics",
        "anchors": ["TimmyJ", "boundaries", "relational_truth"],
        "prior_string_id": "",
        "debug_mode": False,
    }

    result = route_through_qpc(demo_payload)

    print("\n=== QPC Install Demo ===")
    for k, v in result.items():
        if isinstance(v, dict):
            print(f"{k}: {v}")
        else:
            print(f"{k}: {v}")
