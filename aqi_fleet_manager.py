#!/usr/bin/env python3
"""
AQI FLEET MANAGER
=================
The Orchestration Console for the Signature Card Services Digital Workforce.
Use this to monitor agent health, scale instances, and manage the fleet.
"""

import json
import os
import time
import sys
from datetime import datetime

class AQIFleetManager:
    def __init__(self):
        self.manifest_path = "fleet_manifest.json"
        self.manifest = self._load_manifest()
        
    def _load_manifest(self):
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("[!] Manifest not found.")
            return {}

    def status_report(self):
        """Print the current status of the fleet"""
        print("\n" + "="*60)
        print(f"🏛️  {self.manifest.get('fleet_name', 'Unknown Fleet')}")
        print(f"   Version: {self.manifest.get('version')}")
        print(f"   Chairman: {self.manifest.get('chairman')}")
        print("="*60)
        
        print("\n🤖 ACTIVE AGENTS:")
        print(f"{'NAME':<15} {'ROLE':<30} {'STATUS':<10} {'INSTANCES'}")
        print("-" * 70)
        
        for agent in self.manifest.get('agents', []):
            status_icon = "🟢" if agent['status'] == "ACTIVE" else "⚪"
            instances = agent.get('instances', '-')
            print(f"{status_icon} {agent['name']:<13} {agent['role']:<30} {agent['status']:<10} {instances}")

        print("\n⚙️  INFRASTRUCTURE:")
        infra = self.manifest.get('infrastructure', {})
        print(f"   • Relay Port: {infra.get('relay_server_port')}")
        print(f"   • Voice:      {infra.get('voice_provider')}")
        print(f"   • Telephony:  {infra.get('telephony_provider')}")
        print("\n" + "="*60)

    def scale_alan(self, new_instance_count):
        """Simulate scaling the Alan fleet"""
        print(f"\n[FLEET] Requesting scale for 'Alan Jones' -> {new_instance_count} instances...")
        
        # Find Alan
        for agent in self.manifest['agents']:
            if agent['id'] == 'alan_core':
                if new_instance_count > agent['max_instances']:
                    print(f"[!] DENIED. Max instances cap is {agent['max_instances']}.")
                    return
                
                print(f"[FLEET] Provisioning {new_instance_count} virtual lines...")
                time.sleep(1)
                print(f"[FLEET] Allocating memory shards...")
                time.sleep(1)
                agent['instances'] = new_instance_count
                print(f"✅ SUCCESS. Alan Fleet is now running {new_instance_count} concurrent instances.")
                self._save_manifest()
                return

    def activate_alice(self):
        """Activate the Retention Agent"""
        print("\n[FLEET] Attempting to activate 'Alice' (Retention)...")
        for agent in self.manifest['agents']:
            if agent['id'] == 'alice_retention':
                agent['status'] = "ACTIVE"
                print("✅ SUCCESS. Alice is now ONLINE and monitoring merchant health.")
                self._save_manifest()
                return

    def _save_manifest(self):
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=4)

def main():
    fleet = AQIFleetManager()
    
    while True:
        fleet.status_report()
        print("\nCOMMANDS:")
        print("1. Scale Alan (Add Instances)")
        print("2. Activate Alice (Phase 3)")
        print("3. Refresh Status")
        print("4. Exit")
        
        choice = input("\nSelect Command (1-4): ")
        
        if choice == '1':
            count = int(input("Enter target instance count: "))
            fleet.scale_alan(count)
        elif choice == '2':
            fleet.activate_alice()
        elif choice == '3':
            continue
        elif choice == '4':
            print("Exiting Fleet Manager.")
            break
        else:
            print("Invalid command.")
            time.sleep(1)

if __name__ == "__main__":
    main()
