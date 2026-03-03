"""
AQI Merchant Onboarding Stress-Test Pack (v1.0)
-----------------------------------------------

Defines and runs stress scenarios focused on the merchant onboarding flow:

    - high-turn conversations
    - confused merchants
    - angry merchants
    - repeated verification attempts
    - silence / noise

Uses the existing synthetic_call_generator + wrapper.
"""

from __future__ import annotations
from typing import List, Dict, Any, Callable
import time

from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest


# You can adapt this if synthetic_call_generator already supports tags
STRESS_SCENARIOS = [
    "merchant_onboarding_happy_path",
    "merchant_onboarding_confused",
    "merchant_onboarding_angry",
    "merchant_onboarding_silent",
    "merchant_onboarding_repeated_verification",
]


def run_onboarding_stress_test(
    wrapper: VoiceQPCWrapper,
    scenario_runner: Callable[[str, Callable[[bytes], Dict[str, Any]]], None],
    iterations: int = 10,
    delay: float = 0.1,
) -> None:
    """
    Runs onboarding stress scenarios multiple times to test stability.
    scenario_runner: function(scenario_name, send_audio_to_aqi)
    """

    for scenario in STRESS_SCENARIOS:
        print(f"\n=== Stress-testing scenario: {scenario} ===")

        for n in range(iterations):
            trajectory: List[Dict[str, Any]] = []

            def send_audio_to_aqi(audio_bytes: bytes) -> Dict[str, Any]:
                req = VoiceTurnRequest(
                    audio_bytes=audio_bytes,
                    caller_id=f"stress_{scenario}_{n}",
                    source="synthetic",
                    epistemic_layer="merchant_support",
                    anchors=["stress_test", scenario],
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

            scenario_runner(scenario, send_audio_to_aqi)
            print(f"  Iteration {n+1}/{iterations} completed, turns={len(trajectory)}")
            time.sleep(delay)

        print(f"=== Completed stress scenario: {scenario} ===\n")
