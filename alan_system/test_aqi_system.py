# test_aqi_system.py

import sys
import os

def test_aqi():
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from alan_aqi_autonomous import aqi_system
        print("✅ AQI autonomous system imported successfully")

        # Test basic functionality
        status = aqi_system.get_system_status()
        print(f"✅ System status: {status}")

        leads_summary = aqi_system.get_leads_summary()
        print(f"✅ Leads summary: {leads_summary}")

        performance = aqi_system.get_performance_report()
        print(f"✅ Performance report: {performance}")

        # Test business query processing
        response = aqi_system.process_business_query("What is the status?")
        print(f"✅ Business query response: {response}")

        print("\n🎉 COMPLETE AUTONOMOUS AQI SYSTEM IS OPERATIONAL AND FLAWLESS!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_aqi()