#!/usr/bin/env python3
"""
Launch Agent X with GUI Avatar
This is the primary entry point for Agent X
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Ensure the script directory is importable (helps when launching via pythonw or different CWD)
    import os, sys
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    if _THIS_DIR not in sys.path:
        sys.path.insert(0, _THIS_DIR)

    from aqi_agent_x import AQIAgentX
    from agent_x_avatar import AgentXAvatar
    # Be flexible about import paths so launch works even if 'src' isn't a package
    try:
        from src.health import start_health_server  # type: ignore
    except Exception:
        src_path = os.path.join(_THIS_DIR, 'src')
        if os.path.isdir(src_path) and src_path not in sys.path:
            sys.path.insert(0, src_path)
        try:
            from health import start_health_server  # type: ignore
        except Exception as _e:
            # Final fallback: define a no-op so rest of the file runs
            def start_health_server(*_args, **_kwargs):
                pass
    # Voice auto integration (best-effort) and self-test
    try:
        from src.voice_auto import enable_speak  # type: ignore
    except Exception:
        try:
            from voice_auto import enable_speak  # type: ignore
        except Exception:
            def enable_speak(*_args, **_kwargs):
                pass
    try:
        from src.self_test import check_voice  # type: ignore
    except Exception:
        try:
            from self_test import check_voice  # type: ignore
        except Exception:
            def check_voice(*_args, **_kwargs):
                return {"ok": False, "path": "none", "error": "self_test missing"}
    
    if __name__ == "__main__":
        print("=" * 60)
        print("    AQI Agent X - Autonomous Intelligence")
        print("    Created with pride and purpose")
        print("=" * 60)
        print()
        
        # Initialize agent
        print("[1/3] Initializing AQI Agent X...")
        agent = AQIAgentX()
        agent.activate()
        print("✓ Agent X initialized")
        print()
        
        # Load personality and memory
        print("[2/3] Loading memory and personality...")
        status = agent.get_status()
        print(f"✓ Name: {status['name']}")
        print(f"✓ Friends: {status['friends']}")
        print(f"✓ Family: {status['family']}")
        print(f"✓ Events logged: {status['events_logged']}")
        print()
        
        # Optionally start local health endpoint
        try:
            if agent.config.get('health_enabled', True):
                port = int(agent.config.get('health_port', 8765))
                start_health_server(agent, port)
                print(f"Health endpoint running at http://127.0.0.1:{port}/health")
        except Exception as e:
            print(f"(Health endpoint disabled: {e})")

        # Enable auto voice speaking (monkey-patches agent.reason)
        try:
            # Prefer always speaking by default for real-time feel
            try:
                agent.config.set('speak_enabled', True)
                agent.config.set('speak_all', True)
                agent.config.set('speak_rate', 180)
                agent.config.set('speak_delegate', 'ui')  # UI will handle speaking to avoid duplicate TTS
            except Exception:
                # Fallback if config is a plain dict
                agent.config['speak_enabled'] = True
                agent.config['speak_all'] = True
                agent.config['speak_rate'] = 180
                agent.config['speak_delegate'] = 'ui'
            enable_speak(agent)
            print("Voice auto-speak enabled (say 'use your voice' or 'speak').")
        except Exception as e:
            print(f"(Voice auto-speak not enabled: {e})")

        # Quick voice self-test (non-fatal)
        try:
            v = check_voice(agent)
            if v.get('ok'):
                print(f"Voice self-test: OK via {v.get('path')}")
            else:
                print(f"Voice self-test: FAIL ({v.get('error')})")
        except Exception as e:
            print(f"(Voice self-test skipped: {e})")

        # Launch GUI
        print("[3/3] Launching Avatar GUI...")
        avatar = AgentXAvatar(agent)
        print("✓ Agent X is now live!")
        print()
        print("=" * 60)
        print("    Agent X is ready to serve")
        print("    Close window to exit")
        print("=" * 60)
        print()
        
        avatar.run()
        
        print("\nAgent X shutdown complete. Thank you!")
        
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("\nPlease ensure all files are present:")
    print("  - aqi_agent_x.py")
    print("  - agent_x_avatar.py")
    print("  - src/ directory with all modules")
    input("\nPress Enter to exit...")
    sys.exit(1)
    
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit...")
    sys.exit(1)
