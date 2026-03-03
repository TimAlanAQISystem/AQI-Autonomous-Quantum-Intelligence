import sys
from pathlib import Path
import urllib.request
import base64

env_path = Path(r"C:\Users\signa\OneDrive\Desktop\Agent X\Alan_Deployment\config\.env")
if not env_path.exists():
    print(f"Missing .env at {env_path}", file=sys.stderr)
    sys.exit(2)

text = env_path.read_text(encoding='utf-8')
conf = {}
for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        k,v = line.split('=',1)
        conf[k.strip()] = v.strip()

sid = conf.get('TWILIO_ACCOUNT_SID')
token = conf.get('TWILIO_AUTH_TOKEN')
if not sid or not token:
    print('Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in .env', file=sys.stderr)
    sys.exit(2)

url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}.json'
req = urllib.request.Request(url)
auth = base64.b64encode(f"{sid}:{token}".encode('ascii')).decode('ascii')
req.add_header('Authorization', f'Basic {auth}')

out_path = Path(r"C:\Users\signa\OneDrive\Desktop\Agent X\alan_twilio_check.json")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode('utf-8')
        out_path.write_text(body, encoding='utf-8')
        print('Saved Twilio response to', out_path)
        if resp.status != 200:
            print('Non-200 status:', resp.status, file=sys.stderr)
            sys.exit(3)
except Exception as e:
    print('Twilio API request failed:', str(e), file=sys.stderr)
    sys.exit(3)
