#!/usr/bin/env python3
"""
Agent X ConversationRelay Server Runner
Starts the WebSocket server for AI-powered voice conversations with Twilio.
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check and install required dependencies."""
    required_packages = ['websockets', 'twilio']

    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} installed successfully")

def start_conversation_relay_server():
    """Start the ConversationRelay WebSocket server."""
    print("=== Agent X ConversationRelay Server ===")
    print("Starting WebSocket server for AI-powered voice conversations...")
    print()

    # Check dependencies
    check_dependencies()
    print()

    # Set environment variables for server configuration
    os.environ.setdefault('CONVERSATION_RELAY_HOST', '0.0.0.0')
    os.environ.setdefault('CONVERSATION_RELAY_PORT', '8765')

    # Import and run the server
    try:
        from agent_x_conversation_relay_server import main
        import asyncio

        print("Server will be available at:")
        print("  WebSocket URL: ws://localhost:8765")
        print("  Secure WebSocket URL: wss://your-domain.com:8765 (with SSL)")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)

        # Run the server
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nServer shutdown requested by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        return False

    return True

def show_usage_info():
    """Show information about how to use the ConversationRelay server."""
    print("\n=== Usage Information ===")
    print("1. The server is now running on ws://localhost:8765")
    print("2. Update your TwiML to use this WebSocket URL:")
    print('   <ConversationRelay url="ws://localhost:8765" />')
    print()
    print("3. For production, use a secure WebSocket URL:")
    print('   <ConversationRelay url="wss://your-domain.com:8765" />')
    print()
    print("4. The server handles:")
    print("   - Real-time speech-to-text transcription")
    print("   - AI-powered response generation")
    print("   - Text-to-speech synthesis")
    print("   - Session management and conversation history")
    print()
    print("5. To test locally, you can use ngrok to expose the WebSocket:")
    print("   ngrok http 8765")
    print("   Then use: wss://your-ngrok-url.ngrok.io")
    print()

if __name__ == "__main__":
    success = start_conversation_relay_server()
    if success:
        show_usage_info()
    else:
        print("Failed to start ConversationRelay server")
        sys.exit(1)