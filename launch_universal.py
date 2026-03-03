#!/usr/bin/env python3
"""
Agent X - Universal Cross-Platform Launcher
Detects OS and launches appropriate interface
"""
import sys
import os
import platform

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def detect_platform():
    """Detect current platform"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'mac'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'windows'
    else:
        return 'unknown'

def launch_desktop():
    """Launch desktop GUI version"""
    try:
        from aqi_agent_x import AQIAgentX
        from agent_x_avatar import AgentXAvatar
        
        print("=" * 60)
        print("    AQI Agent X - Universal Desktop Launch")
        print(f"    Platform: {platform.system()}")
        print("=" * 60)
        print()
        
        print("[1/3] Initializing AQI Agent X...")
        agent = AQIAgentX()
        agent.activate()
        print("✓ Agent X initialized")
        print()
        
        print("[2/3] Loading memory and personality...")
        status = agent.get_status()
        print(f"✓ Name: {status['name']}")
        print(f"✓ Friends: {status['friends']}")
        print(f"✓ Family: {status['family']}")
        print()
        
        print("[3/3] Launching Avatar GUI...")
        avatar = AgentXAvatar(agent)
        print("✓ Agent X is now live!")
        print()
        print("=" * 60)
        print(f"    Running on {platform.system()}")
        print("    Close window to exit")
        print("=" * 60)
        print()
        
        avatar.run()
        print("\nAgent X shutdown complete. Thank you!")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

def main():
    """Main entry point with platform detection"""
    current_platform = detect_platform()
    print(f"Detected platform: {current_platform}")
    print()
    
    # Desktop platforms
    if current_platform in ['windows', 'mac', 'linux']:
        launch_desktop()
    else:
        print(f"Platform {current_platform} not yet supported for GUI.")
        print("Web interface coming soon!")
        sys.exit(1)

if __name__ == "__main__":
    main()
