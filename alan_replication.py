"""
ALAN REPLICATION ENGINE
========================
Real concurrent call management for Alan's fleet.

The relay server already supports concurrent WebSocket connections
(per-connection state in active_conversations dict). This module
provides the orchestration layer:

1. FLEET CAPACITY — enforces max_instances from fleet_manifest.json
2. CONCURRENT CALLS — tracks all active Alan instances
3. BATCH DIALING — fire multiple calls concurrently (respecting capacity)
4. EXPERIENCE SHARING — wires agent_communication.py so every Alan
   instance learns from every other instance's calls in real-time
5. FLEET STATUS — provides live visibility into all running instances

Architecture:
  - Each Twilio call creates a WebSocket connection to the relay server
  - Each WebSocket connection IS an Alan instance (per-connection state)
  - This module tracks how many are active and enforces the ceiling
  - The relay server + this module together = Hive Mind replication

Created: February 14, 2026
"""

import json
import os
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import the shared experience database (Hive Mind foundation)
from agent_communication import AgentCommunicationHub

logger = logging.getLogger(__name__)


class AlanReplicationEngine:
    """
    Manages concurrent Alan instances (calls).
    
    Each active phone call = 1 Alan instance.
    The relay server handles the actual WebSocket/audio pipeline.
    This engine handles capacity, tracking, and experience sharing.
    """
    
    def __init__(self, manifest_path: str = "fleet_manifest.json"):
        # Load fleet configuration
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
        
        # Fleet limits
        self.max_instances = self.manifest.get("agents", [{}])[0].get("max_instances", 50)
        
        # Active instance tracking
        # Key: call_sid, Value: instance metadata
        self.active_instances: Dict[str, Dict[str, Any]] = {}
        
        # Completed call log (bounded — last 100)
        self.completed_calls: List[Dict[str, Any]] = []
        self._max_completed_log = 100
        
        # Statistics
        self.total_calls_handled = 0
        self.peak_concurrent = 0
        
        # Hive Mind — shared experience database
        self.comm_hub = AgentCommunicationHub()
        
        logger.info(f"[REPLICATION] Engine initialized. Max instances: {self.max_instances}")
    
    def _load_manifest(self) -> dict:
        """Load fleet manifest configuration."""
        try:
            if os.path.exists(self.manifest_path):
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[REPLICATION] Failed to load manifest: {e}")
        return {"agents": [{"max_instances": 50}]}
    
    # =========================================================================
    # CAPACITY MANAGEMENT
    # =========================================================================
    
    @property
    def current_count(self) -> int:
        """Number of currently active Alan instances (calls)."""
        return len(self.active_instances)
    
    @property
    def available_slots(self) -> int:
        """How many more concurrent calls can be accepted."""
        return max(0, self.max_instances - self.current_count)
    
    def can_accept_call(self) -> bool:
        """Check if fleet has capacity for another concurrent call."""
        return self.current_count < self.max_instances
    
    # =========================================================================
    # INSTANCE LIFECYCLE
    # =========================================================================
    
    def register_instance(self, call_sid: str, metadata: Optional[Dict] = None) -> bool:
        """
        Register a new Alan instance (call starting).
        Returns True if accepted, False if at capacity.
        """
        if not self.can_accept_call():
            logger.warning(f"[REPLICATION] REJECTED call {call_sid} — at capacity "
                           f"({self.current_count}/{self.max_instances})")
            return False
        
        instance_info = {
            "call_sid": call_sid,
            "instance_id": f"ALAN-{self.total_calls_handled + 1:04d}",
            "started_at": datetime.now().isoformat(),
            "start_ts": time.time(),
            "status": "active",
            "turns": 0,
            "prospect_name": (metadata or {}).get("prospect_name", "Unknown"),
            "business_name": (metadata or {}).get("business_name", ""),
            "phone_number": (metadata or {}).get("phone_number", ""),
        }
        
        self.active_instances[call_sid] = instance_info
        self.total_calls_handled += 1
        
        # Track peak concurrency
        if self.current_count > self.peak_concurrent:
            self.peak_concurrent = self.current_count
        
        logger.info(f"[REPLICATION] Instance {instance_info['instance_id']} registered "
                     f"(call: {call_sid}, active: {self.current_count}/{self.max_instances})")
        
        # Broadcast to Hive Mind — new instance online
        self.comm_hub.send_message(
            from_agent=instance_info["instance_id"],
            to_agent="all",
            message_type="instance_online",
            message_data={"call_sid": call_sid, "active_count": self.current_count}
        )
        
        return True
    
    def update_instance(self, call_sid: str, turns: int = None, status: str = None):
        """Update an active instance's metadata."""
        if call_sid in self.active_instances:
            if turns is not None:
                self.active_instances[call_sid]["turns"] = turns
            if status is not None:
                self.active_instances[call_sid]["status"] = status
    
    def deregister_instance(self, call_sid: str, outcome: str = "completed",
                            lessons: str = "", merchant_data: Dict = None):
        """
        Deregister an Alan instance (call ended).
        Shares the experience with the Hive Mind.
        """
        if call_sid not in self.active_instances:
            logger.warning(f"[REPLICATION] Cannot deregister unknown call {call_sid}")
            return
        
        instance = self.active_instances.pop(call_sid)
        duration = time.time() - instance["start_ts"]
        
        # Build completed record
        completed = {
            **instance,
            "ended_at": datetime.now().isoformat(),
            "duration_seconds": round(duration, 1),
            "outcome": outcome,
        }
        
        # Bounded completed log
        self.completed_calls.append(completed)
        if len(self.completed_calls) > self._max_completed_log:
            self.completed_calls = self.completed_calls[-self._max_completed_log:]
        
        logger.info(f"[REPLICATION] Instance {instance['instance_id']} deregistered "
                     f"(duration: {duration:.1f}s, outcome: {outcome}, "
                     f"remaining: {self.current_count}/{self.max_instances})")
        
        # Share experience with Hive Mind
        self.comm_hub.share_experience(
            agent_id=instance["instance_id"],
            experience_type=outcome,
            merchant_data=merchant_data or {
                "prospect_name": instance.get("prospect_name"),
                "business_name": instance.get("business_name"),
                "phone_number": instance.get("phone_number"),
            },
            outcome=outcome,
            lessons=lessons or f"Call lasted {duration:.0f}s, {instance.get('turns', 0)} turns"
        )
    
    # =========================================================================
    # HIVE MIND — EXPERIENCE SHARING
    # =========================================================================
    
    def get_relevant_experiences(self, experience_type: str = None, limit: int = 5) -> List[Dict]:
        """
        Pull relevant experiences from the Hive Mind for a new call.
        Other Alan instances' successful strategies become available to all.
        """
        return self.comm_hub.get_shared_experiences(experience_type, limit)
    
    def get_hive_messages(self, instance_id: str = "alan_core") -> List[Dict]:
        """Get coordination messages for an Alan instance."""
        return self.comm_hub.get_messages(instance_id)
    
    # =========================================================================
    # BATCH DIALING
    # =========================================================================
    
    async def prepare_batch(self, leads: List[Dict], max_concurrent: int = 5) -> Dict:
        """
        Validate and prepare a batch of leads for concurrent dialing.
        Returns a plan with accepted/rejected leads based on capacity.
        
        Args:
            leads: List of dicts with at minimum {to: phone_number}
            max_concurrent: Max calls to fire at once (respects fleet ceiling too)
        """
        effective_max = min(max_concurrent, self.available_slots)
        
        accepted = leads[:effective_max]
        queued = leads[effective_max:]
        
        return {
            "accepted": len(accepted),
            "queued": len(queued),
            "effective_max": effective_max,
            "fleet_capacity": f"{self.current_count}/{self.max_instances}",
            "leads_accepted": accepted,
            "leads_queued": queued,
        }
    
    # =========================================================================
    # FLEET STATUS
    # =========================================================================
    
    def get_fleet_status(self) -> Dict:
        """Get comprehensive fleet status for monitoring."""
        return {
            "fleet_name": self.manifest.get("fleet_name", "Signature Card Services Digital Workforce"),
            "engine": "AlanReplicationEngine",
            "capacity": {
                "max_instances": self.max_instances,
                "active_instances": self.current_count,
                "available_slots": self.available_slots,
                "utilization_pct": round(self.current_count / self.max_instances * 100, 1) if self.max_instances > 0 else 0,
            },
            "statistics": {
                "total_calls_handled": self.total_calls_handled,
                "peak_concurrent": self.peak_concurrent,
                "completed_calls_logged": len(self.completed_calls),
            },
            "active_calls": [
                {
                    "instance_id": inst["instance_id"],
                    "call_sid": inst["call_sid"],
                    "prospect": inst.get("prospect_name", "Unknown"),
                    "business": inst.get("business_name", ""),
                    "duration": f"{time.time() - inst['start_ts']:.0f}s",
                    "turns": inst.get("turns", 0),
                    "status": inst.get("status", "active"),
                }
                for inst in self.active_instances.values()
            ],
            "recent_completed": self.completed_calls[-5:] if self.completed_calls else [],
            "hive_mind": {
                "shared_experiences_db": "agent_experiences.db",
                "status": "active",
            },
            "timestamp": datetime.now().isoformat(),
        }


# Singleton instance
_replication_engine: Optional[AlanReplicationEngine] = None

def get_replication_engine() -> AlanReplicationEngine:
    """Get or create the singleton replication engine."""
    global _replication_engine
    if _replication_engine is None:
        _replication_engine = AlanReplicationEngine()
    return _replication_engine
