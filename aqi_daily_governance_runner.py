"""
AQI Daily Governance Runner (v1.0)
----------------------------------

Runs the full voice-governance pipeline:

    1. Merchant onboarding stress tests
    2. Regression harness (sandbox)
    3. Sandbox vs live comparison
    4. Promotion decision scoring
    5. Fused call intelligence export
    6. Governance dashboard summary

This is the daily heartbeat for AQI voice governance.
"""

from __future__ import annotations
import os
import json
import datetime

from synthetic_call_generator import list_scenarios, run_local_simulation
from aqi_voice_qpc_wrapper import VoiceQPCWrapper
from aqi_merchant_onboarding_stress_pack import run_onboarding_stress_test
from aqi_voice_regression_harness import run_voice_regression
from aqi_voice_comparison_harness import run_voice_comparison
from aqi_voice_promotion_decision import evaluate_promotion_readiness, print_promotion_decision
from aqi_voice_governance_dashboard import run_governance_dashboard
from aqi_event_fusion_layer import AQIEventFusionEngine
from aqi_call_intelligence_exporter import (
    export_call_intelligence_json,
    export_call_intelligence_csv,
)


# ============================================================
# Runner
# ============================================================


def run_daily_governance(wrapper: VoiceQPCWrapper) -> None:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = f"governance_runs/{timestamp}"
    os.makedirs(output_root, exist_ok=True)

    print("\n==============================================")
    print("      AQI DAILY VOICE GOVERNANCE RUN")
    print("==============================================")
    print(f"Timestamp: {timestamp}")
    print(f"Output root: {output_root}\n")

    # --------------------------------------------------------
    # 1. Merchant Onboarding Stress Tests
    # --------------------------------------------------------
    print("\n[1] Running Merchant Onboarding Stress Tests...")
    run_onboarding_stress_test(
        wrapper,
        scenario_runner=lambda name, send: run_local_simulation(
            name, send_audio_to_aqi=send, delay=0.1
        ),
        iterations=10,
    )
    print("[1] Stress tests complete.\n")

    # --------------------------------------------------------
    # 2. Regression Harness (Sandbox)
    # --------------------------------------------------------
    print("\n[2] Running Regression Harness (sandbox)...")
    run_voice_regression(wrapper)
    print("[2] Regression complete.\n")

    # --------------------------------------------------------
    # 3. Sandbox vs Live Comparison
    # --------------------------------------------------------
    print("\n[3] Running Sandbox vs Live Comparison...")
    scenarios = list_scenarios()
    run_voice_comparison(wrapper, scenarios)
    print("[3] Comparison complete.\n")

    # --------------------------------------------------------
    # 4. Promotion Decision
    # --------------------------------------------------------
    print("\n[4] Evaluating Promotion Readiness...")
    promotion_report = evaluate_promotion_readiness(wrapper, scenarios)
    print_promotion_decision(promotion_report)

    # Save promotion report
    with open(os.path.join(output_root, "promotion_report.json"), "w", encoding="utf-8") as f:
        json.dump(promotion_report, f, indent=2)

    print("[4] Promotion decision saved.\n")

    # --------------------------------------------------------
    # 5. Fused Call Intelligence Export
    # --------------------------------------------------------
    print("\n[5] Exporting Fused Call Intelligence...")
    fusion_engine = AQIEventFusionEngine(wrapper)

    # Export all fused streams
    for call_sid in fusion_engine.event_log.keys():
        json_path = export_call_intelligence_json(fusion_engine, call_sid)
        csv_path = export_call_intelligence_csv(fusion_engine, call_sid)
        print(f"  Exported call {call_sid}:")
        print(f"    JSON: {json_path}")
        print(f"    CSV:  {csv_path}")

    print("[5] Intelligence export complete.\n")

    # --------------------------------------------------------
    # 6. Governance Dashboard Summary
    # --------------------------------------------------------
    print("\n[6] Running Governance Dashboard Summary...")
    run_governance_dashboard(wrapper, scenarios, compare_sandbox_live=True)
    print("[6] Dashboard complete.\n")

    print("\n==============================================")
    print("     DAILY VOICE GOVERNANCE RUN COMPLETE")
    print("==============================================\n")
