"""Run Agent X as a background service (health endpoint + optional audio manager)
This runner is intended to initialize the AQI agent, start a local health endpoint,
and (optionally) start audio capture in test mode. It runs as a long-lived process.
"""
import time
import os
import sys
import threading

# Ensure local imports work
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Try to import agent
try:
    from aqi_agent_x import AQIAgentX
except Exception as e:
    print(f"Failed to import AQIAgentX: {e}")
    raise

# Health server helper
def start_health(agent, port=8765):
    try:
        try:
            from src.health import start_health_server
        except Exception:
            from health import start_health_server
        server = start_health_server(agent, port)
        print(f"Health server started on 127.0.0.1:{port}")
        return server
    except Exception as e:
        print(f"Health server failed: {e}")
        return None

# Optional audio manager start
def try_start_audio(test_mode=True):
    try:
        import audio_manager as am
        # Use test_mode so we don't depend on Silero in streaming
        audio = am.AudioManager(test_mode=test_mode, debug=False)
        # Try to start input if device exists
        try:
            audio.start_input()
            print("Audio input started (test_mode)")
        except Exception as e:
            print(f"Audio input start failed: {e}")
        return audio
    except Exception as e:
        print(f"AudioManager import failed or not available: {e}")
        return None


def main():
    agent = AQIAgentX(name='Alan')
    agent.activate()

    # Start health endpoint
    start_health(agent, port=int(agent.config.get('health_port', 8765)))

    # Start audio manager in test mode (best-effort)
    audio = try_start_audio(test_mode=True)

    # Keep process alive and log basic heartbeat to agent ledger
    try:
        while True:
            agent.log_event('heartbeat')
            time.sleep(60)
    except KeyboardInterrupt:
        print('Shutdown requested')
        try:
            if audio:
                audio.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
