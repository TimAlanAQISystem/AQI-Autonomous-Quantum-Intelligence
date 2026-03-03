# Agent 1 - Onboarding Specialist
# Equipped with onboarding.py and compliance.py IQcores

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

class Agent1:
    def __init__(self, agent_id: str = "agent_1"):
        self.agent_id = agent_id
        self.iqcores = {}
        self.load_iqcores()
        self.call_history = []
        print(f"AGENT 1 ({self.agent_id}) INITIALIZED - Onboarding Specialist")

    def load_iqcores(self):
        """Load IQcores from Operations folder"""
        try:
            # Import onboarding functions
            from core.onboarding import onboard_merchant
            self.iqcores['onboarding'] = onboard_merchant

            # Import constitutional functions (for compliance)
            from core.constitutional import check_ethics
            self.iqcores['compliance'] = check_ethics

            print("IQcores loaded successfully")
        except ImportError as e:
            print(f"Warning: Could not load IQcores: {e}")
            # Fallback to basic functionality
            self.iqcores = {}

    def handle_call(self, merchant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a merchant onboarding call"""
        print(f"\n{self.agent_id.upper()}: Processing call for {merchant_data.get('business_name', 'Unknown')}")

        # Share experience from previous calls
        shared_exp = comm_hub.get_shared_experiences('onboarding', limit=3)
        if shared_exp:
            print(f"Learning from {len(shared_exp)} shared experiences")

        # Use onboarding IQcore
        if 'onboarding' in self.iqcores:
            response = self.iqcores['onboarding'](merchant_data)
        else:
            response = self.basic_onboarding(merchant_data)

        # Check compliance
        if 'compliance' in self.iqcores:
            compliance_ok = self.iqcores['compliance'](merchant_data, {})
            if not compliance_ok:
                response['compliance_flag'] = True
                response['message'] = "Call escalated for compliance review"

        # Record and share experience
        outcome = "successful" if response.get('interested', False) else "needs_followup"
        lessons = f"Merchant showed interest in {response.get('service_interest', 'general_services')}"

        comm_hub.share_experience(
            self.agent_id, 'onboarding', merchant_data, outcome, lessons
        )

        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'merchant': merchant_data,
            'response': response
        })

        return response

    def basic_onboarding(self, merchant_data: Dict) -> Dict:
        """Basic onboarding logic if IQcores not available"""
        return {
            'message': f"Hello {merchant_data.get('contact_name', 'there')}, this is Agent 1 from Supreme Merchant Services. How can I help you today?",
            'interested': random.choice([True, False]),
            'service_interest': 'payment_processing',
            'next_steps': 'schedule_followup'
        }

    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'iqcores_loaded': list(self.iqcores.keys()),
            'calls_handled': len(self.call_history),
            'last_call': self.call_history[-1] if self.call_history else None
        }

# Initialize agent
agent_1 = Agent1()

if __name__ == "__main__":
    # Test run
    test_merchant = {
        'business_name': 'Test Restaurant',
        'contact_name': 'John Doe',
        'phone': '+1234567890'
    }

    result = agent_1.handle_call(test_merchant)
    print("Test Result:", json.dumps(result, indent=2))
    print("Agent Status:", json.dumps(agent_1.get_status(), indent=2))