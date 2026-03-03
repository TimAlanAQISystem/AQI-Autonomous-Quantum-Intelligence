"""
AQI Voice Governance Dashboard (v1.0)
-------------------------------------

Text-based dashboard that:

    - runs regression harness
    - runs drift detection per scenario
    - (optionally) runs sandbox vs live comparison
    - prints governance-grade summaries

This is a CLI view over your voice governance surface.
"""

from __future__ import annotations
from typing import List, Dict, Any

from synthetic_call_generator import list_scenarios
from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest
from aqi_voice_regression_harness import run_voice_regression
from aqi_voice_drift_detector import detect_voice_drift
from aqi_voice_comparison_harness import run_voice_comparison


def _format_bool(flag: bool) -> str:
    return "OK" if not flag else "FLAGGED"


def _summarize_drift(scenario: str, trajectory: List[Dict[str, Any]]) -> None:
    drift = detect_voice_drift(trajectory)
    print(f"\n[DRIFT SUMMARY] Scenario: {scenario}")
    print(f"  Energy drift:      {_format_bool(drift['energy_drift'])}")
    print(f"  Energy spikes:     {len(drift['energy_spikes'])} spikes")
    print(f"  Stance instability:{_format_bool(drift['stance_instability'])}")
    print(f"  Oscillation:       {_format_bool(drift['oscillation'])}")
    print(f"  Softening:         {_format_bool(drift['softening'])}")


def run_governance_dashboard(
    wrapper: VoiceQPCWrapper,
    scenarios: List[str] | None = None,
    compare_sandbox_live: bool = False,
) -> None:
    """
    High-level governance view:
        - runs regression
        - prints drift summaries
        - optionally runs sandbox vs live comparison
    """
    if scenarios is None:
        scenarios = list_scenarios()

    print("\n=== AQI Voice Governance Dashboard ===\n")
    print(f"Scenarios: {', '.join(scenarios)}")

    # 1. Run regression and drift summaries (sandbox)
    print("\n[STEP 1] Running sandbox regression + drift summaries...")
    for scenario in scenarios:
        trajectory: List[Dict[str, Any]] = []

        def send_audio_to_aqi(audio_bytes: bytes) -> Dict[str, Any]:
            req = VoiceTurnRequest(
                audio_bytes=audio_bytes,
                caller_id=f"dashboard_{scenario}",
                source="synthetic",
                epistemic_layer="merchant_support",
                anchors=["dashboard", scenario],
                sandbox=True,
            )
            resp = wrapper.process_voice_turn(req)
            turn = {
                "transcript": resp.transcript,
                "content": resp.content,
                "stance": resp.stance,
                "energy": resp.energy,
                "sandbox": resp.sandbox,
                "string_id": resp.string_id,
            }
            trajectory.append(turn)
            return turn

        from synthetic_call_generator import run_local_simulation
        run_local_simulation(
            scenario_name=scenario,
            send_audio_to_aqi=send_audio_to_aqi,
            delay=0.2,
        )

        _summarize_drift(scenario, trajectory)

    # 2. Optional sandbox vs live comparison
    if compare_sandbox_live:
        print("\n[STEP 2] Running sandbox vs live comparison...")
        run_voice_comparison(wrapper, scenarios)

    print("\n=== Governance Dashboard Complete ===\n")
