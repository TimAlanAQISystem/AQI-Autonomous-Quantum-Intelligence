"""
AQI Voice Comparison Harness (v1.0)
-----------------------------------

Runs each synthetic scenario twice:
    - sandbox=True  (field equation prototype)
    - sandbox=False (live engine)

Captures trajectories, drift reports, CSV exports, and
prints a promotion-grade comparison report.
"""

from __future__ import annotations

import time
from typing import List, Dict, Any

from synthetic_call_generator import run_local_simulation
from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest
from aqi_voice_drift_detector import detect_voice_drift
from aqi_voice_csv_exporter import export_voice_trajectory_to_csv


# -----------------------------
# Utility: single pass runner
# -----------------------------

def _run_single_pass(
    wrapper: VoiceQPCWrapper,
    scenario: str,
    sandbox: bool,
    delay: float = 0.5,
) -> List[Dict[str, Any]]:
    trajectory: List[Dict[str, Any]] = []

    def send_audio_to_aqi(audio_bytes: bytes) -> Dict[str, Any]:
        req = VoiceTurnRequest(
            audio_bytes=audio_bytes,
            caller_id=f"synthetic_{scenario}",
            source="synthetic",
            epistemic_layer="merchant_support",
            anchors=["voice_comparison", scenario],
            prior_string_id=None,
            sandbox=sandbox,
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

    run_local_simulation(
        scenario_name=scenario,
        send_audio_to_aqi=send_audio_to_aqi,
        delay=delay,
    )

    return trajectory


# -----------------------------
# Trajectory comparison
# -----------------------------

def compare_trajectories(
    sandbox_traj: List[Dict[str, Any]],
    live_traj: List[Dict[str, Any]],
    energy_threshold: float = 0.25,
    stance_threshold: float = 0.30,
) -> Dict[str, Any]:
    divergence_points = []
    length = min(len(sandbox_traj), len(live_traj))

    for idx in range(length):
        s_energy = sandbox_traj[idx].get("energy")
        l_energy = live_traj[idx].get("energy")

        s_stance = sandbox_traj[idx].get("stance") or {}
        l_stance = live_traj[idx].get("stance") or {}

        if s_energy is not None and l_energy is not None:
            if abs(s_energy - l_energy) > energy_threshold:
                divergence_points.append((idx, "energy", s_energy, l_energy))

        for key in set(s_stance.keys()).union(l_stance.keys()):
            sv = s_stance.get(key)
            lv = l_stance.get(key)
            if sv is not None and lv is not None:
                if abs(sv - lv) > stance_threshold:
                    divergence_points.append((idx, f"stance_{key}", sv, lv))

    return {
        "divergence_points": divergence_points,
        "aligned": len(divergence_points) == 0,
    }


# -----------------------------
# Public harness
# -----------------------------

def run_voice_comparison(
    wrapper: VoiceQPCWrapper,
    scenario_list: List[str],
    delay: float = 0.5,
) -> None:
    for scenario in scenario_list:
        print(f"\n=== Comparing scenario: {scenario} ===")

        sandbox_traj = _run_single_pass(wrapper, scenario, sandbox=True, delay=delay)
        sandbox_drift = detect_voice_drift(sandbox_traj)
        sandbox_csv = export_voice_trajectory_to_csv(
            scenario_name=f"{scenario}_sandbox",
            trajectory=sandbox_traj,
        )

        live_traj = _run_single_pass(wrapper, scenario, sandbox=False, delay=delay)
        live_drift = detect_voice_drift(live_traj)
        live_csv = export_voice_trajectory_to_csv(
            scenario_name=f"{scenario}_live",
            trajectory=live_traj,
        )

        comparison = compare_trajectories(sandbox_traj, live_traj)

        print("\n--- Sandbox Drift Report ---")
        print(sandbox_drift)

        print("\n--- Live Drift Report ---")
        print(live_drift)

        print("\n--- Trajectory Comparison ---")
        if comparison["aligned"]:
            print("ENGINES ALIGNED: sandbox and live trajectories match within thresholds.")
        else:
            print("DIVERGENCE DETECTED:")
            for turn, key, s_val, l_val in comparison["divergence_points"]:
                print(f"  Turn {turn}: {key} sandbox={s_val} live={l_val}")

        print("\nCSV files:")
        print("  Sandbox:", sandbox_csv)
        print("  Live:   ", live_csv)

        print("\n==============================\n")
        time.sleep(0.5)
