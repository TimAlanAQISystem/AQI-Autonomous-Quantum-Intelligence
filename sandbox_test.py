#!/usr/bin/env python3
"""
Sandbox environment to test Agent X / Alan functionality
Tests: Agent reasoning, voice generation, conversation flow
"""

import os
import sys
import asyncio
import tempfile
import subprocess

# Add paths
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Test imports
print("=== SANDBOX: Testing Imports ===")
try:
    from agent_alan_business_ai import AgentAlanBusinessAI
    print("✅ AgentAlanBusinessAI imported")
except Exception as e:
    print(f"❌ AgentAlanBusinessAI import failed: {e}")
    AgentAlanBusinessAI = None

try:
    from aqi_agent_x import AQIAgentX
    print("✅ AQIAgentX imported")
except Exception as e:
    print(f"❌ AQIAgentX import failed: {e}")

# Test agent initialization
print("\n=== SANDBOX: Testing Agent Initialization ===")
agent = None
if AgentAlanBusinessAI:
    try:
        agent = AgentAlanBusinessAI()
        agent.activate()
        print("✅ Agent Alan initialized")
    except Exception as e:
        print(f"❌ Agent Alan init failed: {e}")
        agent = None

if agent is None:
    try:
        agent = AQIAgentX(name='Alan')
        print("✅ Fallback to AQIAgentX")
    except Exception as e:
        print(f"❌ AQIAgentX init failed: {e}")
        sys.exit(1)

# Test reasoning
print("\n=== SANDBOX: Testing Agent Reasoning ===")
test_inputs = [
    "Hello, I'm interested in merchant services",
    "What are your rates?",
    "Goodbye"
]

for test_input in test_inputs:
    try:
        import asyncio
        if hasattr(agent, 'reason') and asyncio.iscoroutinefunction(agent.reason):
            reply = asyncio.run(agent.reason(test_input))
        else:
            reply = agent.reason(test_input)
        print(f"Input: '{test_input}'")
        print(f"Reply: '{reply}'")
        print("✅ Reasoning works")
    except Exception as e:
        print(f"❌ Reasoning failed for '{test_input}': {e}")

# Test voice generation
print("\n=== SANDBOX: Testing Voice Generation ===")
def test_voice_generation(text, voice_id="21m00Tcm4TlvDq8ikWAM"):
    """Test ElevenLabs voice generation"""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ No ELEVENLABS_API_KEY set")
        return None

    import requests
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(response.content)
                temp_file = f.name
            print(f"✅ Voice generated: {voice_id} -> {temp_file}")
            # Play it (Windows)
            try:
                subprocess.run(['start', temp_file], shell=True, check=True)
                print("✅ Audio played")
            except:
                print("⚠️ Could not play audio, but file generated")
            return temp_file
        else:
            print(f"❌ Voice API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Voice generation failed: {e}")
        return None

test_voice_generation("Hello, this is Alan speaking with a male voice.")

# Test Twilio simulation
print("\n=== SANDBOX: Testing Twilio Simulation ===")
try:
    from twilio.twiml.voice_response import VoiceResponse, Gather
    response = VoiceResponse()
    gather = response.gather(input="speech", action="/test/gather", method="POST", timeout=5)
    gather.say("Hello from Alan", voice="man")
    twiml = str(response)
    print(f"✅ TwiML generated: {twiml}")
except Exception as e:
    print(f"❌ TwiML generation failed: {e}")

print("\n=== SANDBOX: Complete ===")
print("If all tests pass, the system is ready. If not, check error messages above.")