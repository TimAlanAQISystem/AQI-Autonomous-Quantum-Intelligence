import requests
import json

url = 'http://127.0.0.1:8777/call'
payload = {
    'to': '+14062102346',
    'live': True
}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Call initiated! Status: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Call failed: {e}")