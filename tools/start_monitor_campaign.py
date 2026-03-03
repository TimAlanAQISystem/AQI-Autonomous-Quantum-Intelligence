import requests
import time
import sys
import json

def start_campaign():
    print("Triggering campaign to monitor 5 calls...")
    try:
        # Check status
        status_resp = requests.get("http://localhost:8777/campaign/status", timeout=2)
        if status_resp.status_code == 200:
            status = status_resp.json()
            if status.get("active", False):
                print("Campaign is currently RUNNING. Stopping it to restart with new parameters...")
                stop_resp = requests.post("http://localhost:8777/campaign/stop", timeout=5)
                if stop_resp.status_code == 200:
                    print("Stopped successfully.")
                    time.sleep(1) # Give it a moment to cleanup
                else:
                    print(f"Failed to stop: {stop_resp.text}")
                    sys.exit(1)
        
        # Start campaign
        response = requests.post(
            "http://localhost:8777/campaign/start",
            json={"max_calls": 5, "delay_seconds": 60},
            timeout=5
        )
        
        if response.status_code == 200:
            print("SUCCESS: Campaign started.")
            print(json.dumps(response.json(), indent=2))
            print("\nMonitoring has begun. Calls will be placed with 60s delay.")
            print("To watch live progress, run in a new terminal:")
            print("  python campaign_watch.py")
        elif response.status_code == 409:
            print("WARNING: Campaign already running.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"FAILED: Status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    start_campaign()
