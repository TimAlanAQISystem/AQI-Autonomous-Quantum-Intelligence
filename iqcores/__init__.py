"""
AGENT X — IQ CORES
===================
5 Intelligence Cores that form Agent X's cognitive architecture.

IQCore 1: CoreReasoning     — Multi-step inference, pattern recognition, confidence scoring
IQCore 2: GovernanceAudit   — Decision audit trail, compliance checks, anomaly detection
IQCore 3: LearningThread    — Pattern learning, strategy effectiveness, feedback loops
IQCore 4: SocialGraph       — Relationship management, trust depth, social context
IQCore 5: VoiceEmotion      — Emotional intelligence, empathy calibration, tone management

Orchestrator: Unifies all 5 cores into a single intelligence surface for Agent X.

Architecture:
  Agent X → IQCore Orchestrator → 5 Cores → Unified Intelligence

Created: February 15, 2026
"""

from .core_reasoning import CoreReasoningIQCore
from .governance_audit import GovernanceAuditIQCore
from .learning_thread import LearningThreadIQCore
from .social_graph import SocialGraphIQCore
from .voice_emotion import VoiceEmotionIQCore
from .orchestrator import IQCoreOrchestrator

__all__ = [
    'CoreReasoningIQCore',
    'GovernanceAuditIQCore',
    'LearningThreadIQCore',
    'SocialGraphIQCore',
    'VoiceEmotionIQCore',
    'IQCoreOrchestrator'
]
