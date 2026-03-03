"""
AQI Voice Promotion Decision Script (v1.0)
-----------------------------------------

Runs sandbox vs live comparison on a set of scenarios and emits
a promotion recommendation:

    - "PROMOTE"
    - "HOLD"
    - with reasons

This is the decision helper for flipping the router flag.
"""

from __future__ import annotations
from typing import List, Dict, Any

from synthetic_call_generator import list_scenarios
from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest
from aqi_voice_drift_detector import detect_voice_drift
from aqi_voice_comparison_harness import compare_trajectories, _run_single_pass


def evaluate_promotion_readiness(
    wrapper: VoiceQPCWrapper,
    scenarios: List[str] | None = None,
) -> Dict[str, Any]:
    if scenarios is None:
        scenarios = list_scenarios()

    results = {
        "scenarios": {},
        "overall": {
            "promote": False,
            "reason": "",
        },
    }

    all_aligned = True
    any_drift_flags = False
    reasons: List[str] = []

    for scenario in scenarios:
        # sandbox
        sandbox_traj = _run_single_pass(wrapper, scenario=scenario, sandbox=True, delay=0.2)
        sandbox_drift = detect_voice_drift(sandbox_traj)

        # live
        live_traj = _run_single_pass(wrapper, scenario=scenario, sandbox=False, delay=0.2)
        live_drift = detect_voice_drift(live_traj)

        comparison = compare_trajectories(sandbox_traj, live_traj)

        scenario_result = {
            "sandbox_drift": sandbox_drift,
            "live_drift": live_drift,
            "aligned": comparison["aligned"],
            "divergence_points": comparison["divergence_points"],
        }
        results["scenarios"][scenario] = scenario_result

        if not comparison["aligned"]:
            all_aligned = False
            reasons.append(f"{scenario}: divergence between sandbox and live.")

        # treat any drift in sandbox as a problem
        if (
            sandbox_drift["energy_drift"]
            or sandbox_drift["stance_instability"]
            or sandbox_drift["oscillation"]
            or sandbox_drift["softening"]
        ):
            any_drift_flags = True
            reasons.append(f"{scenario}: sandbox drift flags present.")

    if all_aligned and not any_drift_flags:
        results["overall"]["promote"] = True
        results["overall"]["reason"] = "Sandbox and live aligned across scenarios; no critical drift flags."
    else:
        results["overall"]["promote"] = False
        results["overall"]["reason"] = "; ".join(reasons) or "Unspecified misalignment."

    return results


def print_promotion_decision(report: Dict[str, Any]) -> None:
    print("\n=== AQI Voice Promotion Decision ===\n")
    print(f"PROMOTE: {'YES' if report['overall']['promote'] else 'NO'}")
    print(f"Reason:  {report['overall']['reason']}\n")

    for scenario, data in report["scenarios"].items():
        print(f"- Scenario: {scenario}")
        print(f"  Aligned: {data['aligned']}")
        print(f"  Divergence points: {len(data['divergence_points'])}")
        print(f"  Sandbox drift: {data['sandbox_drift']}")
        print(f"  Live drift:    {data['live_drift']}")
        print()

    print("=== End of Promotion Report ===\n")
