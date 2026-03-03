# Agent 2 - Retention Specialist
# Equipped with retention.py and analytics.py IQcores

import sys
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
import random

# Add paths for IQcores and communication
sys.path.append(r'c:\Users\signa\OneDrive\Desktop\Operations\AQI-10 - Copy - Copy (3)\iqcore')
sys.path.append(r'c:\Users\signa\OneDrive\Desktop\Agent X')

from agent_communication import comm_hub

class Agent2:
    def __init__(self, agent_id: str = "agent_2"):
        self.agent_id = agent_id
        self.iqcores = {}
        self.load_iqcores()
        self.call_history = []
        print(f"AGENT 2 ({self.agent_id}) INITIALIZED - Retention Specialist")

    def load_iqcores(self):
        """Load IQcores from Operations folder"""
        try:
            # Import retention function
            from core.retention import analyze_retention
            self.iqcores['retention'] = analyze_retention

            # Import escalation function (for analytics)
            from core.leasing import escalate_case
            self.iqcores['analytics'] = escalate_case

            print("IQcores loaded successfully")
        except ImportError as e:
            print(f"Warning: Could not load IQcores: {e}")
            self.iqcores = {}

    def handle_call(self, merchant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a merchant retention call"""
        print(f"\n{self.agent_id.upper()}: Processing retention call for {merchant_data.get('business_name', 'Unknown')}")

        # Learn from shared experiences
        shared_exp = comm_hub.get_shared_experiences('retention', limit=3)
        if shared_exp:
            print(f"Learning from {len(shared_exp)} shared retention experiences")

        # Use retention IQcore
        if 'retention' in self.iqcores:
            response = self.iqcores['retention'](merchant_data)
        else:
            response = self.basic_retention(merchant_data)

        # Analytics check
        if 'analytics' in self.iqcores:
            analytics = self.iqcores['analytics'](merchant_data)
            response['analytics_insights'] = analytics

        # Share experience
        outcome = "retained" if response.get('retained', False) else "at_risk"
        lessons = f"Merchant retention factors: {response.get('key_factors', 'pricing_loyalty')}"

        comm_hub.share_experience(
            self.agent_id, 'retention', merchant_data, outcome, lessons
        )

        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'merchant': merchant_data,
            'response': response
        })

        return response

    def basic_retention(self, merchant_data: Dict) -> Dict:
        """Basic retention logic"""
        return {
            'message': f"Hello {merchant_data.get('contact_name', 'valued merchant')}, this is Agent 2 checking on your satisfaction with our services.",
            'retained': random.choice([True, False]),
            'key_factors': 'service_quality',
            'next_steps': 'loyalty_program'
        }

    def get_status(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'iqcores_loaded': list(self.iqcores.keys()),
            'calls_handled': len(self.call_history),
            'last_call': self.call_history[-1] if self.call_history else None
        }

# Initialize agent
agent_2 = Agent2()

if __name__ == "__main__":
    test_merchant = {
        'business_name': 'Existing Client Inc',
        'contact_name': 'Jane Smith',
        'phone': '+1234567891'
    }

    result = agent_2.handle_call(test_merchant)
    print("Test Result:", json.dumps(result, indent=2))
    print("Agent Status:", json.dumps(agent_2.get_status(), indent=2))