"""
AQI Intent Router
-----------------

Facade that forwards AQI intents either to:
- Live QPC-2 chamber (production engine)
- Sandbox QPC-2 prototype (field-based / experimental)

Routing is governed by configuration flags. Default remains the live engine.
Sandbox traffic is tagged, isolated from production state, and logged
for maturation analysis before any promotion.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

from install_qpc import route_through_qpc

# Optional future import for regression harnesses
try:  # pragma: no cover - optional dependency
    from qpc2_compare import run_side_by_side  # noqa: F401
except Exception:  # pragma: no cover - not critical at runtime
    run_side_by_side = None  # type: ignore


# =========================
# Logging setup
# =========================

logger = logging.getLogger("aqi.intent_router")
logger.setLevel(logging.INFO)

sandbox_logger = logging.getLogger("aqi.qpc2_sandbox")
sandbox_logger.setLevel(logging.INFO)


# =========================
# Configuration model
# =========================


@dataclass
class AQIConfig:
    use_qpc2_sandbox: bool
    environment: str
    sandbox_enabled_envs: tuple = ("dev", "staging")


def load_aqi_config() -> AQIConfig:
    env = os.getenv("AQI_ENV", "dev").lower()
    flag = os.getenv("AQI_USE_QPC2_SANDBOX", "false").lower()

    sandbox_allowed = env in ("dev", "staging")
    use_sandbox = sandbox_allowed and flag in {"1", "true", "yes"}

    return AQIConfig(
        use_qpc2_sandbox=use_sandbox,
        environment=env,
    )


# =========================
# Public routing facade
# =========================


def route_intent(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = load_aqi_config()

    if _should_use_sandbox(config):
        return _route_to_sandbox(payload, config)
    return _route_to_live(payload, config)


# =========================
# Routing helpers
# =========================


def _should_use_sandbox(config: AQIConfig) -> bool:
    if not config.use_qpc2_sandbox:
        return False
    if config.environment not in config.sandbox_enabled_envs:
        return False
    return True


def _route_to_live(payload: Dict[str, Any], config: AQIConfig) -> Dict[str, Any]:
    logger.info(
        "Routing intent to LIVE QPC-2",
        extra={"environment": config.environment, "sandbox": False},
    )

    result = dict(route_through_qpc(payload))
    result["sandbox"] = False
    result["router_environment"] = config.environment
    return result


def _route_to_sandbox(payload: Dict[str, Any], config: AQIConfig) -> Dict[str, Any]:
    sandbox_logger.info(
        "Routing intent to SANDBOX QPC-2",
        extra={"environment": config.environment, "sandbox": True},
    )

    sandbox_result = dict(route_through_qpc(payload))
    sandbox_result["sandbox"] = True
    sandbox_result["router_environment"] = config.environment

    _log_sandbox_interaction(payload, sandbox_result, config)
    return sandbox_result


def _log_sandbox_interaction(
    payload: Dict[str, Any],
    result: Dict[str, Any],
    config: AQIConfig,
) -> None:
    record = {
        "environment": config.environment,
        "sandbox": True,
        "input": payload,
        "output": {
            "string_id": result.get("string_id"),
            "content": result.get("content"),
            "stance": result.get("stance"),
            "anchors": result.get("anchors"),
            "scores": result.get("scores"),
            "epistemic_layer": result.get("epistemic_layer"),
            "drift_flags": result.get("drift_flags"),
            "governance_action": result.get("governance_action"),
        },
    }
    sandbox_logger.info("QPC2_SANDBOX_INTERACTION " + json.dumps(record, default=str))


# =========================
# Promotion protocol (documentation only)
# =========================

"""
Promotion checklist:
1. Run automated regression via qpc2_compare.run_side_by_side across diverse scenarios.
2. Export stance & energy trajectories to CSV; review for drift, softening, instability.
3. Obtain governance approval before flipping AQI_USE_QPC2_SANDBOX in production.
4. Only after approval, merge field physics into the live engine and retire sandbox flag.
"""
