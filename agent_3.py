# Agent 3 - Sales Specialist
# Equipped with sales.py and negotiation.py IQcores

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

class Agent3:
    def __init__(self, agent_id: str = "agent_3"):
        self.agent_id = agent_id
        self.iqcores = {}
        self.load_iqcores()
        self.call_history = []
        print(f"AGENT 3 ({self.agent_id}) INITIALIZED - Sales Specialist")

    def load_iqcores(self):
        """Load IQcores from Operations folder"""
        try:
            # Import leasing function (for sales)
            from core.leasing import escalate_case
            self.iqcores['sales'] = escalate_case

            # Import config_loader function (for negotiation)
            from core.config_loader import load_rules
            self.iqcores['negotiation'] = load_rules

            print("IQcores loaded successfully")
        except ImportError as e:
            print(f"Warning: Could not load IQcores: {e}")
            self.iqcores = {}

    def handle_call(self, merchant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a merchant sales call"""
        print(f"\n{self.agent_id.upper()}: Processing sales call for {merchant_data.get('business_name', 'Unknown')}")

        # Learn from shared experiences
        shared_exp = comm_hub.get_shared_experiences('sales', limit=3)
        if shared_exp:
            print(f"Learning from {len(shared_exp)} shared sales experiences")

        # Use sales IQcore
        if 'sales' in self.iqcores:
            response = self.iqcores['sales'](merchant_data)
        else:
            response = self.basic_sales(merchant_data)

        # Negotiation check
        if 'negotiation' in self.iqcores:
            negotiated_terms = self.iqcores['negotiation']("sales_rules.yaml")
            response['negotiated_terms'] = negotiated_terms

        # Share experience
        outcome = "closed" if response.get('closed_deal', False) else "followup_needed"
        lessons = f"Sales approach: {response.get('effective_tactics', 'value_proposition')}"

        comm_hub.share_experience(
            self.agent_id, 'sales', merchant_data, outcome, lessons
        )

        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'merchant': merchant_data,
            'response': response
        })

        return response

    def basic_sales(self, merchant_data: Dict) -> Dict:
        """Basic sales logic"""
        return {
            'message': f"Hello {merchant_data.get('contact_name', 'prospect')}, this is Agent 3 with an exciting opportunity for your business.",
            'closed_deal': random.choice([True, False]),
            'effective_tactics': 'roi_focus',
            'next_steps': 'contract_signing'
        }

    def get_status(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'iqcores_loaded': list(self.iqcores.keys()),
            'calls_handled': len(self.call_history),
            'last_call': self.call_history[-1] if self.call_history else None
        }

# Initialize agent
agent_3 = Agent3()

if __name__ == "__main__":
    test_merchant = {
        'business_name': 'Prospect LLC',
        'contact_name': 'Bob Johnson',
        'phone': '+1234567892'
    }

    result = agent_3.handle_call(test_merchant)
    print("Test Result:", json.dumps(result, indent=2))
    print("Agent Status:", json.dumps(agent_3.get_status(), indent=2))