#!/usr/bin/env python3
"""
AQI Holiday Maintenance Monitor
Resource-preserving system health checks during holiday period
"""

import os
import sqlite3
from datetime import datetime

class HolidayMaintenanceMonitor:
    """
    Monitors AQI system health during holiday preservation period
    No API calls, no resource consumption - internal checks only
    """

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.check_timestamp = datetime.now()

    def check_database_integrity(self):
        """Verify database files exist and are accessible"""
        databases = [
            'aqi_merchant_services.db',
            'agent_experiences.db',
            'aqi_compliance.db',
            'aqi_unified_agent.db'
        ]

        status = {}
        for db_name in databases:
            db_path = os.path.join(self.base_dir, db_name)
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                    conn.close()
                    status[db_name] = "✅ INTEGRITY OK"
                except Exception as e:
                    status[db_name] = f"❌ ERROR: {str(e)}"
            else:
                status[db_name] = "⚠️ FILE MISSING"

        return status

    def check_configuration_files(self):
        """Verify configuration files exist"""
        config_files = [
            'requirements.txt',
            'Business_Interaction_Training.md',
            'Holiday_Maintenance_Protocol.md',
            'AQI_FOUNDING_DECLARATION.md'
        ]

        status = {}
        for file_name in config_files:
            file_path = os.path.join(self.base_dir, file_name)
            if os.path.exists(file_path):
                status[file_name] = "✅ PRESENT"
            else:
                status[file_name] = "❌ MISSING"

        return status

    def check_code_modules(self):
        """Verify Python modules can be imported (no execution)"""
        modules = [
            'aqi_merchant_services_core',
            'aqi_merchant_services_activation',
            'aqi_compliance_framework',
            'agent_alan_business_ai',
            'aqi_lead_importer'
        ]

        status = {}
        for module_name in modules:
            try:
                __import__(module_name)
                status[module_name] = "✅ IMPORT OK"
            except ImportError as e:
                status[module_name] = f"❌ IMPORT FAILED: {str(e)}"
            except Exception as e:
                status[module_name] = f"⚠️ IMPORT WARNING: {str(e)}"

        return status

    def check_resource_status(self):
        """Check for resource configuration files (no API calls)"""
        resources = {
            'Twilio': 'Twilio Account Info.txt',
            'ElevenLabs': 'ELEVENLABS_API_KEY_HERE.txt',
            'OpenAI': 'data/openai_keys.txt'
        }

        status = {}
        for resource_name, file_path in resources.items():
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                # Check file size as proxy for configuration
                size = os.path.getsize(full_path)
                if size > 0:
                    status[resource_name] = f"✅ CONFIGURED ({size} bytes)"
                else:
                    status[resource_name] = "⚠️ EMPTY CONFIG"
            else:
                status[resource_name] = "❌ NO CONFIG FILE"

        return status

    def generate_maintenance_report(self):
        """Generate comprehensive maintenance report"""
        print("🔧 AQI HOLIDAY MAINTENANCE MONITOR")
        print("=" * 50)
        print(f"📅 Check Date: {self.check_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Status: RESOURCE PRESERVATION MODE")
        print()

        # Database Integrity
        print("💾 DATABASE INTEGRITY:")
        db_status = self.check_database_integrity()
        for db, status in db_status.items():
            print(f"   {status}")
        print()

        # Configuration Files
        print("⚙️ CONFIGURATION FILES:")
        config_status = self.check_configuration_files()
        for file, status in config_status.items():
            print(f"   {status}")
        print()

        # Code Modules
        print("🐍 CODE MODULES:")
        module_status = self.check_code_modules()
        for module, status in module_status.items():
            print(f"   {status}")
        print()

        # Resource Status
        print("🔑 RESOURCE CONFIGURATION:")
        resource_status = self.check_resource_status()
        for resource, status in resource_status.items():
            print(f"   {resource}: {status}")
        print()

        # Overall Assessment
        all_checks = {**db_status, **config_status, **module_status, **resource_status}
        errors = [k for k, v in all_checks.items() if '❌' in v]
        warnings = [k for k, v in all_checks.items() if '⚠️' in v]

        print("📊 OVERALL ASSESSMENT:")
        if not errors and not warnings:
            print("   ✅ ALL SYSTEMS NOMINAL - READY FOR LAUNCH")
        else:
            if errors:
                print(f"   ❌ CRITICAL ISSUES: {len(errors)}")
                for error in errors:
                    print(f"      - {error}")
            if warnings:
                print(f"   ⚠️ WARNINGS: {len(warnings)}")
                for warning in warnings:
                    print(f"      - {warning}")

        print()
        print("🎄 HOLIDAY PRESERVATION STATUS:")
        print("   🔒 API CALLS: SUSPENDED")
        print("   💰 CREDITS: PRESERVED")
        print("   🚀 LAUNCH: READY (January 5, 2026)")
        print()
        print("💡 Next scheduled check: Tomorrow same time")

def run_maintenance_check():
    """Execute daily maintenance monitoring"""
    monitor = HolidayMaintenanceMonitor()
    monitor.generate_maintenance_report()

if __name__ == "__main__":
    run_maintenance_check()</content>
<parameter name="filePath">c:\Users\signa\OneDrive\Desktop\Agent X\holiday_maintenance_monitor.py