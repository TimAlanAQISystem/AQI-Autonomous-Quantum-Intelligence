"""
launch_mobile_server.py - Start Agent X mobile web interface
Works on iOS, Android, and any device with a web browser
"""
import os
import sys
import socket

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from aqi_agent_x import AQIAgentX
    from mobile_interface import start_mobile_server
    
    def get_local_ip():
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    def main():
        print("=" * 60)
        print("AGENT X - MOBILE WEB INTERFACE")
        print("=" * 60)
        
        # Initialize agent
        print("\n[1/3] Initializing Agent X...")
        agent = AQIAgentX()
        agent.activate()
        print("✓ Agent X initialized")
        
        # Load memories
        print("\n[2/3] Loading memories...")
        agent.memory.load()
        print("✓ Memories loaded")
        
        # Start mobile server
        print("\n[3/3] Starting mobile web server...")
        local_ip = get_local_ip()
        port = 8080
        
        print("\n" + "=" * 60)
        print("MOBILE SERVER READY!")
        print("=" * 60)
        print(f"\n📱 Access from this computer:")
        print(f"   http://localhost:{port}")
        print(f"\n📱 Access from phone/tablet on same WiFi:")
        print(f"   http://{local_ip}:{port}")
        print(f"\n💡 Add to home screen for app-like experience!")
        print("\nPress Ctrl+C to stop the server\n")
        
        # Start server (blocks until Ctrl+C)
        start_mobile_server(agent, port)
    
    if __name__ == "__main__":
        try:
            main()
        except KeyboardInterrupt:
            print("\n\nShutting down mobile server...")
            print("Goodbye! 👋")
        except Exception as e:
            print(f"\nError: {e}")
            input("Press Enter to exit...")

except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required files are in place")
    input("Press Enter to exit...")
