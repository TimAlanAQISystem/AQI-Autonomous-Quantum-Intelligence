"""
aqi_fix_orchestrator.py

AQI Fix Orchestrator: collects artifacts, has AQI review them, emits FixPlan for Grok to execute.
"""

import dataclasses
import datetime
from typing import List, Optional, Dict, Any
import json
import logging
import os
import subprocess
import requests
from twilio.rest import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclasses.dataclass
class TwilioArtifact:
    """Raw Twilio-facing artifacts: logs, webhook configs, error pages."""
    call_sid: Optional[str]
    phone_number: Optional[str]
    raw_console_html: Optional[str]      # Twilio page HTML or JSON export
    api_payload: Optional[Dict[str, Any]]
    errors: List[str]


@dataclasses.dataclass
class BackendArtifact:
    """Backend logs and status for a given window."""
    log_snippet: str                     # stderr/stdout slice around the failure
    health_status: str                   # "running", "crashed", "degraded"
    details: Optional[str] = None


@dataclasses.dataclass
class TunnelArtifact:
    """Tunnel state around the failure."""
    provider: str                        # "ngrok"
    public_url: Optional[str]
    inspector_raw: Optional[Dict[str, Any]]
    errors: List[str]


@dataclasses.dataclass
class AQIRelationalDiagnosticArtifact:
    """Your AQI relational diag snapshot as JSON."""
    raw_json: Dict[str, Any]


@dataclasses.dataclass
class AQIFixPlanStep:
    """One actionable step Grok (or another agent) should perform."""
    actor: str                           # "TwilioAPI", "BackendConfig", "Tunnel", "Codebase"
    action_type: str                     # "update_env_var", "change_webhook", "restart_service", etc.
    description: str                     # human-readable explanation
    payload: Dict[str, Any]              # machine-usable data (e.g., env var name/value)


@dataclasses.dataclass
class AQIFixPlan:
    """Structured plan AQI emits after reviewing all artifacts."""
    summary: str
    root_causes: List[str]
    steps: List[AQIFixPlanStep]
    created_at: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), default=str, indent=2)


def aqi_review_and_generate_fix_plan(
    twilio: TwilioArtifact,
    backend: BackendArtifact,
    tunnel: TunnelArtifact,
    diag: AQIRelationalDiagnosticArtifact,
) -> AQIFixPlan:
    """
    Central review function.
    In practice, this is where you call your AQI model/agent with all JSON,
    and it responds with a structured fix plan.
    Here we scaffold the behavior you'll enforce.
    """

    # Minimal example logic: live-first, guided by your current failure pattern
    root_causes = []
    steps: List[AQIFixPlanStep] = []

    # Example: tunnel missing or unreachable
    if not tunnel.public_url or "Failed to resolve" in " ".join(tunnel.errors):
        root_causes.append("Tunnel URL is invalid or not resolvable from backend environment.")

        # Use the tunnel provider
        if tunnel.provider == "ngrok":
            command = "taskkill /IM ngrok.exe /F & ngrok http 8777"
        elif tunnel.provider == "cloudflared":
            command = "taskkill /IM cloudflared.exe /F & cloudflared tunnel --url http://localhost:8777"
        else:
            command = "echo Unknown tunnel provider"

        steps.append(AQIFixPlanStep(
            actor="Tunnel",
            action_type="start_tunnel",
            description="Kill any existing ngrok process and start a fresh HTTPS tunnel on the backend port, extracting the new public URL.",
            payload={
                "command": "taskkill /IM ngrok.exe /F & ngrok http 8777",
                "port": 8777
            },
        ))

        steps.append(AQIFixPlanStep(
            actor="BackendConfig",
            action_type="update_env_var",
            description="Update PUBLIC_TUNNEL_URL in runtime and in .env to match the newly created tunnel URL.",
            payload={
                "env_var": "PUBLIC_TUNNEL_URL",
                "value_source": "extracted_ngrok_url"
            },
        ))

        steps.append(AQIFixPlanStep(
            actor="TwilioAPI",
            action_type="update_webhooks",
            description="Point Twilio voice and status webhooks to the new PUBLIC_TUNNEL_URL routes.",
            payload={
                "phone_number": twilio.phone_number,
                "voice_path": "/twilio/voice",
                "status_path": "/twilio/status"
            },
        ))

        steps.append(AQIFixPlanStep(
            actor="Backend",
            action_type="restart_service",
            description="Restart Agent X Control Service / backend so it is live and bound to the correct port using updated configuration.",
            payload={
                "restart_method": "configured_backend_restart_command"
            },
        ))

        steps.append(AQIFixPlanStep(
            actor="Verification",
            action_type="verify_tunnel_and_backend",
            description="Verify that the tunnel is reachable and the backend responds correctly at Twilio routes.",
            payload={
                "checks": [
                    "tunnel_https_reachability",
                    "backend_twilio_voice_route",
                    "backend_twilio_status_route"
                ]
            },
        ))

    # Example: AI never engaged and call duration short
    diag_json = diag.raw_json
    primary_cause = diag_json.get("primary_root_cause", "")
    if "Call completed quickly" in primary_cause:
        root_causes.append("Twilio → Tunnel → Backend path broken before AI engagement.")

        steps.append(AQIFixPlanStep(
            actor="Backend",
            action_type="verify_route",
            description="Verify that /twilio/voice route exists and responds with valid TwiML/logic.",
            payload={
                "path": "/twilio/voice",
            },
        ))

    # Outbound-specific failures
    if "Outbound webhook probe failed" in primary_cause:
        root_causes.append("Outbound TwiML delivery failed - backend /twilio/outbound route issue.")

        steps.append(AQIFixPlanStep(
            actor="Backend",
            action_type="verify_route",
            description="Verify that /twilio/outbound route exists and returns valid TwiML.",
            payload={
                "path": "/twilio/outbound",
            },
        ))

        steps.append(AQIFixPlanStep(
            actor="Backend",
            action_type="check_logs",
            description="Check backend logs for errors in outbound handler or Alan integration.",
            payload={
                "log_check": "outbound_handler_errors",
            },
        ))

    if "Twilio account error" in primary_cause:
        root_causes.append("Twilio account or credentials issue preventing outbound calls.")

        steps.append(AQIFixPlanStep(
            actor="TwilioAPI",
            action_type="verify_credentials",
            description="Verify Twilio account SID, auth token, and phone number are valid.",
            payload={
                "checks": ["account_balance", "phone_verification", "api_access"],
            },
        ))

    if "Twilio rejected number" in primary_cause:
        root_causes.append("Invalid or unreachable phone number in outbound call list.")

        steps.append(AQIFixPlanStep(
            actor="Data",
            action_type="validate_numbers",
            description="Validate and clean outbound call list - remove invalid numbers.",
            payload={
                "validation_rules": ["format_check", "carrier_check", "do_not_call_check"],
            },
        ))

    if "Call completed quickly without AI engagement" in primary_cause and "outbound" in str(diag_json).lower():
        root_causes.append("Outbound call connected but AI failed to engage.")

        steps.append(AQIFixPlanStep(
            actor="AI",
            action_type="verify_alan_integration",
            description="Verify Alan/AQI is properly integrated in outbound handler.",
            payload={
                "check_alan": True,
                "check_audio_generation": True,
            },
        ))

    # Fallback summary if none set
    if not root_causes:
        root_causes.append("Unknown – AQI could not determine a clear root cause from artifacts.")

    summary = " | ".join(root_causes)

    return AQIFixPlan(
        summary=summary,
        root_causes=root_causes,
        steps=steps,
    )


def run_aqi_full_review_and_fix_plan(
    twilio_artifact: TwilioArtifact,
    backend_artifact: BackendArtifact,
    tunnel_artifact: TunnelArtifact,
    diag_artifact: AQIRelationalDiagnosticArtifact,
) -> AQIFixPlan:
    """
    Top-level orchestrator:
    - You feed it all artifacts.
    - It calls AQI review.
    - It returns a fix plan for Grok to execute.
    """

    logger.info("[AQI] Starting full relational review of artifacts.")
    plan = aqi_review_and_generate_fix_plan(
        twilio=twilio_artifact,
        backend=backend_artifact,
        tunnel=tunnel_artifact,
        diag=diag_artifact,
    )

    logger.info("[AQI] Fix plan generated:")
    logger.info(plan.to_json())

    # Here is where you hand off to Grok:
    # - Send plan.to_json() to Grok's endpoint
    # - Grok interprets steps and executes (Twilio API updates, env changes, restart, etc.)

    return plan


# ========= Grok Execution Side =========

def execute_shell_command(command: str):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }


def extract_tunnel_url(stdout: str, provider: str) -> str:
    for line in stdout.splitlines():
        if "https://" in line:
            if provider == "ngrok" and "ngrok-free.dev" in line:
                return line.strip().split(" ")[-1]
            elif provider == "cloudflared" and "trycloudflare.com" in line:
                return line.strip().split(" ")[-1]
    return None


def update_env_var(env_var: str, value: str):
    os.environ[env_var] = value
    # Update .env file
    try:
        with open('.env', 'a') as f:
            f.write(f"{env_var}={value}\n")
    except Exception as e:
        logger.warning(f"Failed to update .env: {e}")


def update_twilio_webhooks(phone_number: str, base_url: str):
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    voice = f"{base_url}/twilio/voice"
    status = f"{base_url}/twilio/status"

    client = Client(sid, token)
    numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
    if numbers:
        number = numbers[0]
        number.update(
            voice_url=voice,
            voice_method="POST",
            status_callback=status,
            status_callback_method="POST"
        )
        return f"Updated webhooks for {phone_number}"
    else:
        raise Exception(f"Phone number {phone_number} not found")


def restart_backend():
    # Placeholder: kill and restart
    subprocess.run("taskkill /IM python.exe /F", shell=True, capture_output=True)
    subprocess.Popen(["python", "run_agent_service_full.py"])  # Adjust to your main script


def grok_execute_fix_plan(plan: AQIFixPlan) -> Dict[str, Any]:
    """
    Grok's side: receives AQIFixPlan and executes each step.
    Returns a report of what was done.
    """
    report = {
        "executed_steps": [],
        "errors": [],
        "summary": plan.summary,
    }

    for step in plan.steps:
        try:
            result = grok_execute_step(step)
            report["executed_steps"].append({
                "step": step.description,
                "result": result,
            })
        except Exception as e:
            report["errors"].append({
                "step": step.description,
                "error": str(e),
            })

    return report


def grok_execute_step(step: AQIFixPlanStep) -> str:
    """
    Execute a single AQIFixPlanStep based on actor and action_type.
    """
    if step.actor == "Tunnel" and step.action_type == "start_tunnel":
        command = step.payload["command"]
        provider = step.payload.get("provider", "ngrok")
        result = execute_shell_command(command)
        if result["success"]:
            new_url = extract_tunnel_url(result["stdout"], provider)
            if new_url:
                update_env_var("PUBLIC_TUNNEL_URL", new_url)
                return f"Started tunnel, extracted URL: {new_url}, updated env"
            else:
                return f"Started tunnel but failed to extract URL: {result['stdout']}"
        else:
            raise Exception(f"Tunnel start failed: {result['stderr']}")

    elif step.actor == "BackendConfig" and step.action_type == "update_env_var":
        env_var = step.payload["env_var"]
        value = os.environ.get('PUBLIC_TUNNEL_URL', step.payload.get("value", ""))
        update_env_var(env_var, value)
        return f"Updated {env_var} to {value}"

    elif step.actor == "TwilioAPI" and step.action_type == "update_webhooks":
        phone = step.payload["phone_number"]
        base_url = os.environ.get('PUBLIC_TUNNEL_URL', '')
        result = update_twilio_webhooks(phone, base_url)
        return result

    elif step.actor == "Backend" and step.action_type == "restart_service":
        restart_backend()
        return "Restarted backend service"

    elif step.actor == "Verification" and step.action_type == "verify_tunnel_and_backend":
        url = os.environ.get('PUBLIC_TUNNEL_URL', '')
        checks = step.payload.get("checks", [])
        errors = []
        for check in checks:
            try:
                if check == "tunnel_https_reachability":
                    resp = requests.get(url, timeout=10)
                    if not resp.ok:
                        errors.append(f"Tunnel not reachable: {resp.status_code}")
                elif check == "backend_twilio_voice_route":
                    resp = requests.post(f"{url}/twilio/voice", timeout=10)
                    if resp.status_code not in [200, 201]:
                        errors.append(f"Voice route failed: {resp.status_code}")
                elif check == "backend_twilio_status_route":
                    resp = requests.post(f"{url}/twilio/status", timeout=10)
                    if resp.status_code not in [200, 201]:
                        errors.append(f"Status route failed: {resp.status_code}")
            except Exception as e:
                errors.append(f"{check} error: {e}")
        if errors:
            raise Exception(f"Verification failed: {errors}")
        return f"Verification passed for checks: {checks}"

    elif step.actor == "Backend" and step.action_type == "verify_route":
        path = step.payload["path"]
        url = os.environ.get('PUBLIC_TUNNEL_URL', 'http://localhost:8777')
        full_url = f"{url}{path}"
        try:
            resp = requests.post(full_url, timeout=10)
            if resp.status_code in [200, 201]:
                return f"Route {path} verified: {resp.status_code}"
            else:
                raise Exception(f"Route {path} returned {resp.status_code}")
        except Exception as e:
            raise Exception(f"Route verification failed: {e}")

    elif step.actor == "Backend" and step.action_type == "check_logs":
        # Placeholder - in real implementation, would parse logs
        return "Log check completed - implement log parsing logic"

    elif step.actor == "TwilioAPI" and step.action_type == "verify_credentials":
        sid = os.environ.get('TWILIO_ACCOUNT_SID')
        token = os.environ.get('TWILIO_AUTH_TOKEN')
        phone = os.environ.get('TWILIO_PHONE_NUMBER')
        
        client = Client(sid, token)
        try:
            # Test account access
            account = client.api.accounts(sid).fetch()
            balance = account.balance
            # Test phone number
            numbers = client.incoming_phone_numbers.list(phone_number=phone)
            if numbers:
                return f"Credentials verified - balance: {balance}, phone: {phone}"
            else:
                raise Exception(f"Phone number {phone} not found in account")
        except Exception as e:
            raise Exception(f"Credential verification failed: {e}")

    elif step.actor == "Data" and step.action_type == "validate_numbers":
        # Placeholder - in real implementation, would validate call list
        return "Number validation completed - implement validation logic"

    elif step.actor == "AI" and step.action_type == "verify_alan_integration":
        # Placeholder - in real implementation, would test Alan/AQI
        return "Alan integration verified - implement testing logic"

    else:
        return f"Unknown step: {step.actor} {step.action_type}"


# Example usage
if __name__ == "__main__":
    # Real artifacts from diagnostic
    twilio_artifact = TwilioArtifact(
        call_sid="CAd33b42e0ff10440583fd762946923e45",
        phone_number="+14067322659",
        raw_console_html=None,
        api_payload=None,
        errors=["Direct HTTP probes to voice and status webhooks failed"],
    )

    backend_artifact = BackendArtifact(
        log_snippet="",
        health_status="running",
    )

    tunnel_artifact = TunnelArtifact(
        provider="cloudflared",
        public_url="https://cancelled-postage-possibly-rio.trycloudflare.com",
        inspector_raw=None,
        errors=["Tunnel URL not reachable from backend"],
    )

    diag_artifact = AQIRelationalDiagnosticArtifact(
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

    plan = run_aqi_full_review_and_fix_plan(
        twilio_artifact,
        backend_artifact,
        tunnel_artifact,
        diag_artifact,
    )

    print("Fix Plan:")
    print(plan.to_json())

    # Execute
    report = grok_execute_fix_plan(plan)
    print("Execution Report:")
    print(json.dumps(report, indent=2))