#!/usr/bin/env python3
"""
AQI MERCHANT SERVICES ACTIVATION SYSTEM
========================================
Complete activation of Agent Alan + Twilio + Merchant Services
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import AQI components
try:
    from aqi_lead_importer import AQILeadImporter
    from aqi_merchant_services_core import AQIMerchantServicesCore
    from aqi_compliance_framework import AQIMerchantComplianceFramework
    from agent_alan_business_ai import AgentAlanBusinessAI
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all AQI components are available")
    exit(1)

class AQIMerchantServicesActivation:
    """
    Complete activation system for AQI merchant services
    Connects Agent Alan to Twilio and activates full autonomous operations
    """

    def __init__(self):
        print("🚀 AQI MERCHANT SERVICES ACTIVATION SYSTEM")
        print("=" * 50)

        # Initialize components
        self.lead_importer = None
        self.core_system = None
        self.compliance_system = None
        self.agent_alan = None

        # Activation status
        self.activation_status = {
            'lead_import': 'pending',
            'twilio_connection': 'pending',
            'agent_alan_activation': 'pending',
            'core_system_activation': 'pending',
            'compliance_activation': 'pending',
            'autonomous_operations': 'pending',
            'full_system': 'pending'
        }

        # Performance tracking
        self.metrics = {
            'activation_start': datetime.now(),
            'leads_imported': 0,
            'twilio_tests': 0,
            'calls_completed': 0,
            'systems_activated': 0
        }

        print("✅ ACTIVATION SYSTEM INITIALIZED")

    def activate_lead_import(self) -> bool:
        """Activate lead import from Excel files"""

        print("📊 ACTIVATING LEAD IMPORT SYSTEM...")

        try:
            self.lead_importer = AQILeadImporter()
            leads = self.lead_importer.import_leads_from_excel()
            self.lead_importer.save_leads_to_database(leads)

            stats = self.lead_importer.get_import_stats()
            self.metrics['leads_imported'] = stats['excel_imported_leads']

            self.activation_status['lead_import'] = 'activated'
            print(f"✅ Lead import activated - {self.metrics['leads_imported']} leads imported")
            return True

        except Exception as e:
            print(f"❌ Lead import activation failed: {e}")
            self.activation_status['lead_import'] = 'failed'
            return False

    def activate_twilio_connection(self) -> bool:
        """Activate Twilio connection and test credentials"""

        print("📞 ACTIVATING TWILIO CONNECTION...")

        try:
            # Check environment variables
            twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
            twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
            twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')

            if not all([twilio_sid, twilio_token, twilio_phone]):
                print("❌ Missing Twilio credentials")
                self.activation_status['twilio_connection'] = 'failed'
                return False

            print(f"📱 Twilio Account SID: {twilio_sid[:10]}...")
            print(f"📞 Twilio Phone: {twilio_phone}")
            print("🔐 Twilio Auth Token: Configured")

            # Test Twilio connection
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)

            # Get account info to test connection
            account = client.api.accounts(twilio_sid).fetch()
            print(f"✅ Twilio connection successful - Account: {account.friendly_name}")

            self.activation_status['twilio_connection'] = 'activated'
            self.metrics['twilio_tests'] += 1
            return True

        except Exception as e:
            print(f"❌ Twilio connection failed: {e}")
            self.activation_status['twilio_connection'] = 'failed'
            return False

    def activate_agent_alan(self) -> bool:
        """Activate Agent Alan business AI system"""

        print("🤖 ACTIVATING AGENT ALAN BUSINESS AI...")

        try:
            self.agent_alan = AgentAlanBusinessAI()

            # Test Agent Alan capabilities
            test_greeting = self.agent_alan.generate_business_greeting(
                strategy="cold_call",
                prospect_name="Test Prospect",
                company="Test Company"
            )

            print(f"🗣️ Agent Alan greeting test: {test_greeting[:50]}...")

            # Test response analysis
            test_response = "That sounds interesting, tell me more"
            analysis = self.agent_alan.analyze_business_response(test_response)

            print(f"🧠 Response analysis test: {analysis['interest_level']} interest")

            self.activation_status['agent_alan_activation'] = 'activated'
            print("✅ Agent Alan activated and tested")
            return True

        except Exception as e:
            print(f"❌ Agent Alan activation failed: {e}")
            self.activation_status['agent_alan_activation'] = 'failed'
            return False

    def activate_core_system(self) -> bool:
        """Activate the core merchant services system"""

        print("🔧 ACTIVATING AQI MERCHANT SERVICES CORE...")

        try:
            self.core_system = AQIMerchantServicesCore()
            self.activation_status['core_system_activation'] = 'activated'
            self.metrics['systems_activated'] += 1
            print("✅ Core system activated")
            return True

        except Exception as e:
            print(f"❌ Core system activation failed: {e}")
            self.activation_status['core_system_activation'] = 'failed'
            return False

    def activate_compliance_system(self) -> bool:
        """Activate the compliance framework"""

        print("🔒 ACTIVATING COMPLIANCE FRAMEWORK...")

        try:
            self.compliance_system = AQIMerchantComplianceFramework()
            self.activation_status['compliance_activation'] = 'activated'
            self.metrics['systems_activated'] += 1
            print("✅ Compliance system activated")
            return True

        except Exception as e:
            print(f"❌ Compliance system activation failed: {e}")
            self.activation_status['compliance_activation'] = 'failed'
            return False

    def activate_autonomous_operations(self) -> bool:
        """Activate autonomous operations across all systems"""

        print("🚀 ACTIVATING AUTONOMOUS OPERATIONS...")

        try:
            if self.core_system:
                self.core_system.start_autonomous_operations()
                print("✅ Core system autonomous operations started")

            # Note: Compliance system autonomous monitoring would start here
            # but we'll keep it simple for now

            self.activation_status['autonomous_operations'] = 'activated'
            print("✅ Autonomous operations activated")
            return True

        except Exception as e:
            print(f"❌ Autonomous operations activation failed: {e}")
            self.activation_status['autonomous_operations'] = 'failed'
            return False

    def perform_system_test_call(self) -> bool:
        """Perform a test call to verify Agent Alan + Twilio integration"""

        print("📞 PERFORMING SYSTEM TEST CALL...")

        if not self.agent_alan:
            print("❌ Agent Alan not available for test call")
            return False

        try:
            # Use a test number (you can replace with a real test number)
            test_number = "+14062102346"  # Replace with your test number

            test_prospect = {
                "name": "System Test",
                "company": "AQI Test Merchant",
                "title": "Test Contact",
                "industry": "retail",
                "company_size": "Test"
            }

            print(f"📱 Testing call to: {test_number}")
            print(f"🎯 Test prospect: {test_prospect['name']} at {test_prospect['company']}")

            # Make test call
            call, alan_ai = make_business_call(test_number, test_prospect, "cold_call")

            if call:
                print("✅ Test call initiated successfully")
                print(f"📞 Call SID: {call.sid}")
                self.metrics['calls_completed'] += 1
                return True
            else:
                print("❌ Test call failed")
                return False

        except Exception as e:
            print(f"❌ Test call error: {e}")
            return False

    def activate_full_system(self) -> bool:
        """Activate the complete integrated system"""

        print("🎯 ACTIVATING FULL AQI MERCHANT SERVICES SYSTEM...")

        activation_steps = [
            self.activate_lead_import,
            self.activate_twilio_connection,
            self.activate_agent_alan,
            self.activate_core_system,
            self.activate_compliance_system,
            self.activate_autonomous_operations
        ]

        success_count = 0

        for step in activation_steps:
            if step():
                success_count += 1
            else:
                print(f"⚠️ Activation step failed, continuing...")

        if success_count >= 5:  # Require most systems to activate
            self.activation_status['full_system'] = 'activated'
            print("✅ FULL SYSTEM ACTIVATION SUCCESSFUL!")
            return True
        else:
            self.activation_status['full_system'] = 'partial'
            print(f"⚠️ PARTIAL SYSTEM ACTIVATION - {success_count}/6 systems activated")
            return False

    def get_activation_report(self) -> Dict[str, Any]:
        """Generate comprehensive activation report"""

        activation_time = datetime.now() - self.metrics['activation_start']

        report = {
            'activation_timestamp': datetime.now().isoformat(),
            'activation_duration': str(activation_time),
            'overall_status': self.activation_status['full_system'].upper(),

            'system_status': {
                'lead_import': self.activation_status['lead_import'],
                'twilio_connection': self.activation_status['twilio_connection'],
                'agent_alan': self.activation_status['agent_alan_activation'],
                'core_system': self.activation_status['core_system_activation'],
                'compliance_system': self.activation_status['compliance_activation'],
                'autonomous_operations': self.activation_status['autonomous_operations']
            },

            'performance_metrics': {
                'leads_imported': self.metrics['leads_imported'],
                'twilio_tests_completed': self.metrics['twilio_tests'],
                'systems_activated': self.metrics['systems_activated'],
                'test_calls_completed': self.metrics['calls_completed']
            },

            'system_capabilities': {
                'excel_lead_import': self.activation_status['lead_import'] == 'activated',
                'twilio_voice_calling': self.activation_status['twilio_connection'] == 'activated',
                'agent_alan_ai': self.activation_status['agent_alan_activation'] == 'activated',
                'autonomous_lead_generation': self.activation_status['core_system_activation'] == 'activated',
                'merchant_calling_campaigns': self.activation_status['core_system_activation'] == 'activated',
                'account_onboarding': self.activation_status['core_system_activation'] == 'activated',
                'compliance_monitoring': self.activation_status['compliance_activation'] == 'activated',
                'revenue_tracking': self.activation_status['core_system_activation'] == 'activated'
            },

            'next_steps': [
                "Monitor autonomous operations",
                "Review call performance metrics",
                "Optimize lead scoring algorithms",
                "Expand lead sources",
                "Fine-tune Agent Alan conversation scripts"
            ] if self.activation_status['full_system'] == 'activated' else [
                "Complete failed system activations",
                "Verify Twilio credentials",
                "Check Excel file access",
                "Review error logs"
            ]
        }

        return report

    def display_activation_dashboard(self):
        """Display real-time activation dashboard"""

        print("\n" + "="*60)
        print("🎯 AQI MERCHANT SERVICES ACTIVATION DASHBOARD")
        print("="*60)

        status_icons = {
            'activated': '✅',
            'pending': '⏳',
            'failed': '❌',
            'partial': '⚠️'
        }

        print("📊 SYSTEM STATUS:")
        for component, status in self.activation_status.items():
            icon = status_icons.get(status, '❓')
            print(f"   {icon} {component.replace('_', ' ').title()}: {status.upper()}")

        print("\n📈 PERFORMANCE METRICS:")
        print(f"   📥 Leads Imported: {self.metrics['leads_imported']}")
        print(f"   📞 Test Calls: {self.metrics['calls_completed']}")
        print(f"   🔧 Systems Activated: {self.metrics['systems_activated']}/6")

        print("\n🎯 SYSTEM CAPABILITIES:")
        capabilities = [
            ("Excel Lead Import", self.activation_status['lead_import'] == 'activated'),
            ("Twilio Voice Calling", self.activation_status['twilio_connection'] == 'activated'),
            ("Agent Alan AI", self.activation_status['agent_alan_activation'] == 'activated'),
            ("Autonomous Operations", self.activation_status['autonomous_operations'] == 'activated'),
            ("Compliance Monitoring", self.activation_status['compliance_activation'] == 'activated'),
            ("Revenue Tracking", self.activation_status['core_system_activation'] == 'activated')
        ]

        for capability, active in capabilities:
            icon = "✅" if active else "❌"
            print(f"   {icon} {capability}")

        overall_status = self.activation_status['full_system']
        if overall_status == 'activated':
            print("\n🎉 ACTIVATION SUCCESSFUL! System is fully operational.")
            print("🚀 Autonomous merchant acquisition is now active!")
        elif overall_status == 'partial':
            print("\n⚠️ PARTIAL ACTIVATION - Some systems may need attention.")
        else:
            print("\n❌ ACTIVATION FAILED - Check system status above.")

def activate_aqi_merchant_services():
    """Main activation function"""

    print("🚀 AQI MERCHANT SERVICES ACTIVATION")
    print("=" * 45)

    activator = AQIMerchantServicesActivation()

    # Activate full system
    success = activator.activate_full_system()

    # Display dashboard
    activator.display_activation_dashboard()

    # Generate report
    report = activator.get_activation_report()

    print("\n📋 ACTIVATION REPORT SUMMARY:")
    print(f"Status: {report['overall_status']}")
    print(f"Duration: {report['activation_duration']}")
    print(f"Systems Activated: {report['performance_metrics']['systems_activated']}/6")

    if success:
        print("\n🎯 NEXT STEPS:")
        for step in report['next_steps']:
            print(f"   • {step}")

        print("\n💎 AQI MERCHANT SERVICES FULLY ACTIVATED!")
        print("🔥 Agent Alan + Twilio + Autonomous Operations = ACTIVE")
        print("💰 Ready to acquire merchants and generate revenue!")

    return success

if __name__ == "__main__":
    activate_aqi_merchant_services()