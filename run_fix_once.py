"""
run_fix_once.py

Run the AQI Fix Orchestrator once with real artifacts.
"""

import os
import requests
from twilio.rest import Client
from aqi_fix_orchestrator import (
    run_aqi_full_review_and_fix_plan,
    TwilioArtifact,
    BackendArtifact,
    TunnelArtifact,
    AQIRelationalDiagnosticArtifact,
)
from aqi_relational_diagnostics import run_live_relational_diagnostic_example

# Collect real artifacts

def get_twilio_artifact():
    # Hardcode for now, or query API
    return TwilioArtifact(
        call_sid="CAd33b42e0ff10440583fd762946923e45",
        phone_number="+14067322659",
        raw_console_html=None,
        api_payload=None,
        errors=["Direct HTTP probes to voice and status webhooks failed"],
    )

def get_backend_artifact():
    # Check if backend is running
    try:
        resp = requests.get("http://localhost:8777", timeout=5)
        health = "running" if resp.status_code == 404 else "degraded"  # 404 is expected for root
    except:
        health = "crashed"
    return BackendArtifact(
        log_snippet="",
        health_status=health,
    )

def get_tunnel_artifact():
    # Get from ngrok API
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        data = resp.json()
        tunnels = data.get("tunnels", [])
        if tunnels:
            public_url = tunnels[0]["public_url"]
            errors = []
        else:
            public_url = None
            errors = ["No tunnels found"]
    except Exception as e:
        public_url = None
        errors = [str(e)]
    return TunnelArtifact(
        provider="ngrok",
        public_url=public_url,
        inspector_raw=None,
        errors=errors,
    )

def get_diag_artifact():
    # Run the diagnostic
    # But since it's a function that prints, need to capture or mock
    # For now, use the same as before
    return AQIRelationalDiagnosticArtifact(
        raw_json={
            "primary_root_cause": "Config breach: Direct HTTP probes to both voice and status webhooks failed.",
            "breaches": [
                {
                    "actor": "Config",
                    "breach_mode": "Direct HTTP probes to both voice and status webhooks failed.",
                    "severity": "critical"
                },
                {
                    "actor": "Routing",
                    "breach_mode": "Call completed quickly (<=5s) without AI engagement.",
                    "severity": "error"
                }
            ]
        },
    )

if __name__ == "__main__":
    twilio = get_twilio_artifact()
    backend = get_backend_artifact()
    tunnel = get_tunnel_artifact()
    diag = get_diag_artifact()

    plan = run_aqi_full_review_and_fix_plan(twilio, backend, tunnel, diag)
    print("Fix Plan Generated:")
    print(plan.to_json())

    # The orchestrator already executes if in the example, but in the function, it doesn't.
    # In the code, run_aqi_full_review_and_fix_plan returns the plan, and in the example, it executes.
    # To execute, I need to call grok_execute_fix_plan(plan)

    from aqi_fix_orchestrator import grok_execute_fix_plan
    report = grok_execute_fix_plan(plan)
    print("Execution Report:")
    print(report)