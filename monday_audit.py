"""ALAN MONDAY READINESS AUDIT"""
import os, json, sys

print('='*60)
print('ALAN MONDAY READINESS AUDIT')
print('='*60)

# 1. Core Services
print('\n--- CORE SERVICES ---')
checks = {}

# Load .env if needed
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

key = os.environ.get('OPENAI_API_KEY', '')
checks['OpenAI API Key'] = 'SET' if key and len(key) > 10 else 'MISSING'

for var in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']:
    val = os.environ.get(var, '')
    checks[var] = 'SET' if val and len(val) > 5 else 'MISSING'

el = os.environ.get('ELEVENLABS_API_KEY', '')
checks['ElevenLabs Key'] = 'SET' if el and len(el) > 5 else 'NOT SET (uses OpenAI TTS)'

for k, v in checks.items():
    status = '[OK]' if 'MISSING' not in v else '[!!]'
    print(f'  {status} {k}: {v}')

# 2. Alan's persona
print('\n--- ALAN PERSONA ---')
if os.path.exists('alan_persona.json'):
    with open('alan_persona.json') as f:
        persona = json.load(f)
    name = persona.get('name', 'NOT SET')
    role = persona.get('role', persona.get('title', 'NOT SET'))
    print(f'  [OK] Persona file: EXISTS')
    print(f'  [OK] Name: {name}')
    print(f'  [OK] Role: {role}')
else:
    print('  [!!] alan_persona.json: MISSING')

if os.path.exists('agent_alan_config.json'):
    with open('agent_alan_config.json') as f:
        config = json.load(f)
    print(f'  [OK] Agent config: EXISTS ({len(config)} keys)')
else:
    print('  [!!] agent_alan_config.json: MISSING')

# 3. Database
print('\n--- DATA/STATE ---')
for db in ['alan_business.db', 'agent_x.db', 'aqi_agent_x.db', 'mip_memory.db']:
    if os.path.exists(db):
        size = os.path.getsize(db)
        print(f'  [OK] {db}: {size:,} bytes')
    else:
        print(f'  [--] {db}: not found')

# 4. Tunnel URL
print('\n--- CONNECTIVITY ---')
for f in ['active_tunnel_url.txt', 'active_tunnel_url_fixed.txt']:
    if os.path.exists(f):
        url = open(f).read().strip()
        print(f'  [OK] {f}: {url}')
    else:
        print(f'  [!!] {f}: MISSING')

# 5. Key files
print('\n--- CRITICAL FILES ---')
critical = [
    'control_api_fixed.py',
    'aqi_conversation_relay_server.py',
    'agent_alan_business_ai.py',
    'aqi_voice_module.py',
    'aqi_deep_layer.py',
    'qpc_kernel.py',
    'alan_state_machine.py',
    'alan_guardian_engine.py',
    'adaptive_closing.py',
    'alan_persona.json',
    'agent_alan_config.json',
]
for f in critical:
    if os.path.exists(f):
        lines = len(open(f, encoding='utf-8', errors='ignore').readlines())
        print(f'  [OK] {f}: {lines} lines')
    else:
        print(f'  [!!] {f}: MISSING')

# 6. QPC
print('\n--- QPC GOVERNANCE ---')
qpc_files = ['qpc/__init__.py', 'qpc/identity.py', 'qpc/program.py', 
             'qpc/coherence.py', 'qpc/state.py', 'qpc/noise.py', 'qpc/logical_agent.py']
for f in qpc_files:
    exists = os.path.exists(f)
    print(f'  {"[OK]" if exists else "[!!]"} {f}: {"EXISTS" if exists else "MISSING"}')

# 7. Voice/TTS config
print('\n--- VOICE CONFIGURATION ---')
try:
    from aqi_conversation_relay_server import AQIConversationRelayServer
    print('  [OK] Relay server: IMPORTABLE')
except Exception as e:
    print(f'  [!!] Relay server import: {e}')

# 8. Compliance / Safety
print('\n--- COMPLIANCE/SAFETY ---')
safety_files = [
    'aqi_compliance_framework.py',
    'alan_guardian_engine.py',
    'ALAN_COMPLIANCE_MATRIX.md',
]
for f in safety_files:
    if os.path.exists(f):
        print(f'  [OK] {f}: EXISTS')
    else:
        print(f'  [--] {f}: not found')

# 9. Agent North Portal
print('\n--- AGENT NORTH PORTAL ---')
north_files = []
for f in os.listdir('.'):
    if 'north' in f.lower() or 'portal' in f.lower() or 'connector' in f.lower():
        north_files.append(f)
if north_files:
    for f in north_files:
        print(f'  [OK] {f}')
else:
    print('  [--] No north/portal files found in root')

# 10. Email capability
print('\n--- EMAIL/COMMUNICATION ---')
smtp_user = os.environ.get('SMTP_USERNAME', '')
smtp_email = os.environ.get('EMAIL_ADDRESS', '')
if os.path.exists('ALAN_EMAIL_NODE_CONFIG.json'):
    with open('ALAN_EMAIL_NODE_CONFIG.json') as f:
        email_conf = json.load(f)
    print(f'  [OK] Email config: EXISTS')
else:
    print(f'  [--] ALAN_EMAIL_NODE_CONFIG.json: not found')

print('\n' + '='*60)
print('AUDIT COMPLETE')
print('='*60)
