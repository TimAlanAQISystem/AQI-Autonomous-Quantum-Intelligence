"""
AQI Voice Regression Harness (v1.0)
-----------------------------------

Runs synthetic voice scenarios through the full AQI voice pipeline:
    synthetic_call_generator -> aqi_voice_qpc_wrapper -> QPC-2

Captures per-turn stance/energy trajectories for governance review.
"""

from __future__ import annotations

import time
from typing import List, Dict, Any

from synthetic_call_generator import run_local_simulation, list_scenarios
from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest


def log_turn(scenario: str, turn_index: int, result: Dict[str, Any]) -> None:
    print(f"\n[{scenario}] Turn {turn_index}")
    print(f"  transcript: {result.get('transcript')}")
    print(f"  content:    {result.get('content')}")
    print(f"  stance:     {result.get('stance')}")
    print(f"  energy:     {result.get('energy')}")
    print(f"  sandbox:    {result.get('sandbox')}")
    print(f"  string_id:  {result.get('string_id')}")


def log_summary(scenario: str, trajectory: List[Dict[str, Any]]) -> None:
    energies = [t.get("energy") for t in trajectory if t.get("energy") is not None]
    stance_keys = set()
    for t in trajectory:
        stance = t.get("stance")
        if isinstance(stance, dict):
            stance_keys.update(stance.keys())

    print("\n==============================")
    print(f"Scenario Summary: {scenario}")
    print("==============================")
    print(f"Total turns: {len(trajectory)}")
    print(f"Energy samples: {len(energies)}")
    if energies:
        print(f"Energy min/max: {min(energies)} / {max(energies)}")
    print(f"Stance keys observed: {sorted(list(stance_keys))}")
    print("==============================\n")


def run_voice_regression(
    wrapper: VoiceQPCWrapper,
    scenario_list: List[str] | None = None,
    delay: float = 0.5,
) -> None:
    if scenario_list is None:
        scenario_list = list_scenarios()

    for scenario in scenario_list:
        print(f"\n=== Running scenario: {scenario} ===")

        trajectory: List[Dict[str, Any]] = []

        def send_audio_to_aqi(audio_bytes: bytes) -> Dict[str, Any]:
            req = VoiceTurnRequest(
                audio_bytes=audio_bytes,
                caller_id=f"synthetic_{scenario}",
                source="synthetic",
                epistemic_layer="merchant_support",
                anchors=["voice_regression", scenario],
                prior_string_id=None,
                sandbox=True,
            )
            resp = wrapper.process_voice_turn(req)
            result = {
                "transcript": resp.transcript,
                "content": resp.content,
                "stance": resp.stance,
                "energy": resp.energy,
                "sandbox": resp.sandbox,
                "string_id": resp.string_id,
            }
            trajectory.append(result)
            return result

        run_local_simulation(
            scenario_name=scenario,
            send_audio_to_aqi=send_audio_to_aqi,
            delay=delay,
        )

        for i, turn in enumerate(trajectory):
            log_turn(scenario, i, turn)

        log_summary(scenario, trajectory)
        time.sleep(0.5)
