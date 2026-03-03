"""
Phase 4 Call Trace — Pydantic Model
=====================================
Canonical data contract for Phase 4 → Phase 5 ingestion.
All Phase 5 tools assume this shape.

Aligned with AQI 0.1mm Chip enforcement organs and Continuum Map.
"""

try:
    from pydantic import BaseModel
except ImportError:
    # Fallback: use dataclasses if pydantic not installed
    import dataclasses
    import warnings
    warnings.warn("pydantic not installed — using dataclass fallback")

    class _BaseMeta(type):
        pass

    class BaseModel(metaclass=_BaseMeta):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

from typing import Optional, List, Dict, Any


class MerchantProfile(BaseModel):
    business_type: Optional[str] = None
    size: Optional[str] = None
    prior_processing: Optional[str] = None


class Metadata(BaseModel):
    timestamp_start: str
    timestamp_end: str
    merchant_profile: MerchantProfile


class PromptLayers(BaseModel):
    Identity: str
    Ethics: str
    Personality: str
    Knowledge: str
    Mission: str
    Output: str


class TurnContext(BaseModel):
    mission_escalation: Optional[bool] = False
    objection_branch: Optional[str] = None
    close_attempt: Optional[bool] = False
    output_complexity: Optional[str] = "normal"
    supervisor_flags: Optional[Dict[str, Any]] = None


class HealthSnapshot(BaseModel):
    organism_level: int
    telephony_state: str


class Turn(BaseModel):
    turn_index: int
    fsm_prev_state: str
    fsm_event: str
    fsm_state: str
    prompt_layers: PromptLayers
    context: TurnContext
    health_snapshot: HealthSnapshot


class HealthTrajectoryEntry(BaseModel):
    turn_index: int
    organism_level: int
    telephony_state: str


class TelephonyTrajectoryEntry(BaseModel):
    turn_index: int
    telephony_state: str


class OutcomeVector(BaseModel):
    appointment_set: bool
    soft_decline: bool
    hard_decline: bool
    telephony_unusable: bool
    organism_unfit: bool


class FinalBlock(BaseModel):
    fsm_state: str
    exit_reason: str
    health_trajectory: List[HealthTrajectoryEntry]
    telephony_trajectory: List[TelephonyTrajectoryEntry]
    outcome_vector: OutcomeVector


class Phase4CallTrace(BaseModel):
    call_id: str
    metadata: Metadata
    turns: List[Turn]
    final: FinalBlock
