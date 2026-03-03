"""
System Coordinator
Central orchestration of all safety and intelligence systems
"""

import time
import logging
from typing import Dict, Any, Tuple
from enum import Enum

from emergency_override_system import EmergencyOverrideSystem
from post_generation_hallucination_scanner import PostGenerationHallucinationScanner
from merchant_identity_persistence import MerchantIdentityPersistence
from multi_turn_strategic_planning import MultiTurnStrategicPlanner
from bias_auditing_system import BiasAuditingSystem

logger = logging.getLogger(__name__)


class SystemPriority(Enum):
    EOS = 1          # always wins
    PGHS = 2         # content safety
    SUPERVISOR = 3   # identity/tone/scope
    MTSP = 4         # planning
    MIP = 5          # relationship logging
    BAS = 6          # async, never blocks


class SystemCoordinator:
    """
    Single choke point for all system coordination.
    Priority order: EOS → PGHS → Supervisor → MTSP → MIP → BAS
    """

    def __init__(
        self,
        eos: EmergencyOverrideSystem,
        pghs: PostGenerationHallucinationScanner,
        supervisor,  # AlanSupervisor
        mtsp: MultiTurnStrategicPlanner,
        mip: MerchantIdentityPersistence,
        bas: BiasAuditingSystem,
        config: Dict[str, Any],
        metrics=None
    ):
        self.eos = eos
        self.pghs = pghs
        self.supervisor = supervisor
        self.mtsp = mtsp
        self.mip = mip
        self.bas = bas
        self.config = config
        self.metrics = metrics or SimpleMetrics()
        self.logger = logging.getLogger("SystemCoordinator")

    def process_llm_output(self, llm_output: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Central processing pipeline with priority enforcement.
        Returns (safe_output, metadata)
        """
        start = time.time()
        metadata = {}

        # 0) EOS check - can we even talk to merchant?
        if self.eos.is_merchant_shutdown():
            return self.eos.get_safe_mode_response(), {"eos_shutdown": True}

        # 1) PGHS (if enabled and latency OK)
        if self.config.get("pghs_enabled", True):
            pghs_start = time.time()
            safe_output, major = self.pghs.scan(llm_output, context)
            pghs_latency = (time.time() - pghs_start) * 1000

            self.metrics.observe("pghs_latency_ms", pghs_latency)
            metadata["pghs_latency_ms"] = pghs_latency
            metadata["pghs_major_violation"] = major

            # Latency guard
            if pghs_latency > self.config.get("pghs_budget_ms", 50):
                self.metrics.inc("pghs_degraded")
                self.logger.warning(f"[COORDINATOR] PGHS exceeded budget: {pghs_latency:.1f}ms")
                # In severe cases, could bypass PGHS
                # safe_output = llm_output

            if major:
                # EOS already triggered inside PGHS
                metadata["eos_triggered"] = True
                return safe_output, metadata
        else:
            safe_output = llm_output

        # 2) Supervisor (identity/tone/scope check)
        if self.supervisor:
            try:
                if hasattr(self.supervisor, 'validate_response_compliance'):
                    self.supervisor.validate_response_compliance(safe_output, context)
                elif hasattr(self.supervisor, 'check'):
                    safe_output = self.supervisor.check(safe_output, context)
            except Exception as e:
                self.logger.warning(f"[COORDINATOR] Supervisor check skipped: {e}")
        
        supervised_output = safe_output

        # 3) MTSP + MIP (non-blocking updates)
        if self.config.get("mtsp_enabled", True):
            try:
                self.mtsp.update_async(context)
            except Exception as e:
                self.logger.error(f"[COORDINATOR] MTSP update failed: {e}")
                self.metrics.inc("mtsp_degraded")

        if self.config.get("mip_enabled", True):
            try:
                merchant_id = context.get("merchant_id") or context.get("phone_number")
                if merchant_id and self.mip:
                    call_data = {
                        "archetype": context.get("archetype"),
                        "archetype_confidence": context.get("archetype_confidence"),
                        "objection": context.get("last_objection"),
                        "trajectory": context.get("trajectory"),
                        "outcome": context.get("outcome"),
                    }
                    # Only update if there's meaningful data
                    if any(v for v in call_data.values()):
                        self.mip.update_profile_from_call(merchant_id, call_data)
            except Exception as e:
                self.logger.error(f"[COORDINATOR] MIP update failed: {e}")
                self.metrics.inc("mip_degraded")

        # 4) BAS runs on its own schedule (not here)

        total_latency = (time.time() - start) * 1000
        self.metrics.observe("coordinator_latency_ms", total_latency)
        metadata["total_latency_ms"] = total_latency

        return supervised_output, metadata


class SimpleMetrics:
    """Lightweight metrics collector with bounded memory."""
    MAX_OBSERVATIONS = 1000  # Per-metric cap to prevent unbounded growth

    def __init__(self):
        self.counters = {}
        self.observations = {}

    def inc(self, name: str):
        self.counters[name] = self.counters.get(name, 0) + 1

    def observe(self, name: str, value: float):
        if name not in self.observations:
            self.observations[name] = []
        obs = self.observations[name]
        obs.append(value)
        # Prevent memory leak: keep only the most recent observations
        if len(obs) > self.MAX_OBSERVATIONS:
            self.observations[name] = obs[-self.MAX_OBSERVATIONS:]
