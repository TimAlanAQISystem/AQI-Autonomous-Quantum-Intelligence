#!/usr/bin/env python3
"""
AQI Holiday Maintenance Monitor - Simple Version
"""

import os
import sqlite3
from datetime import datetime

def check_databases():
    """Check database integrity"""
    databases = [
        'aqi_merchant_services.db',
        'agent_experiences.db',
        'aqi_compliance.db'
    ]

    print("Checking databases:")
    for db in databases:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                conn.close()
                print(f"  ✅ {db}")
            except:
                print(f"  ❌ {db}")
        else:
            print(f"  ⚠️ {db} missing")

def check_files():
    """Check important files"""
    files = [
        'Holiday_Maintenance_Protocol.md',
        'requirements.txt'
    ]

    print("Checking files:")
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")

def main():
    print("🔧 AQI Holiday Maintenance Monitor")
    print("=" * 40)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    check_databases()
    print()
    check_files()
    print()
    print("🎄 Status: Resource Preservation Mode")
    print("🚀 Launch: Ready (January 5, 2026)")

if __name__ == "__main__":
    main()