# alan_dns_monitor.py

import time
import socket
import json
import os
from datetime import datetime

from alan_config import JSON_MEMORY_PATH
from alan_memory import load_json_memory, save_json_memory


def check_dns_resolution(domain: str, expected_ip: str = None) -> bool:
    """
    Check if DNS resolution is working for a domain.
    Returns True if DNS resolves successfully.
    """
    try:
        resolved_ip = socket.gethostbyname(domain)
        if expected_ip:
            return resolved_ip == expected_ip
        return True
    except socket.gaierror:
        return False


def check_connection_completion(domain: str, port: int = 80) -> bool:
    """
    Check if we can actually connect to the domain (beyond just DNS resolution).
    This tests full connection completion.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((domain, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def update_dns_status(status: str, details: dict = None):
    """
    Update DNS status in JSON memory.
    Status can be: 'pending', 'resolving', 'completed', 'failed'
    """
    data = load_json_memory()
    data['dns_status'] = {
        'status': status,
        'last_checked': datetime.utcnow().isoformat(),
        'details': details or {}
    }
    save_json_memory(data)


def get_dns_status():
    """Get current DNS status from memory."""
    data = load_json_memory()
    return data.get('dns_status', {'status': 'unknown'})


def notify_dns_completion():
    """
    Called when DNS is fully completed.
    This can trigger notifications, beeps, or integration with Alan voice system.
    """
    print("🎉 DNS COMPLETION DETECTED!")

    # Update status
    update_dns_status('completed', {
        'message': 'DNS propagation and connection completion finalized',
        'timestamp': datetime.utcnow().isoformat()
    })

    # Here you can add:
    # - PC beep notification
    # - Integration with Alan voice system to speak notification
    # - Send notification to other systems

    # Simple beep (Windows)
    try:
        import winsound
        winsound.Beep(800, 500)  # 800Hz for 500ms
    except ImportError:
        # Fallback: print notification
        print("\a")  # ASCII bell

    print("DNS is now fully completed and connections are ready!")


def dns_monitor_loop(target_domain: str, check_interval: int = 60):
    """
    Main DNS monitoring loop.
    Checks DNS resolution and connection completion periodically.

    Args:
        target_domain: Domain to monitor (e.g., 'your-app.ngrok.io')
        check_interval: Seconds between checks (default 60)
    """
    print(f"Starting DNS monitor for {target_domain}")
    print(f"Checking every {check_interval} seconds...")

    update_dns_status('monitoring', {'target_domain': target_domain})

    while True:
        current_status = get_dns_status()

        # Skip if already completed
        if current_status.get('status') == 'completed':
            print("DNS already completed. Monitor stopping.")
            break

        print(f"[{datetime.utcnow().isoformat()}] Checking DNS for {target_domain}...")

        # Check DNS resolution
        dns_ok = check_dns_resolution(target_domain)
        if not dns_ok:
            print("❌ DNS not resolving yet...")
            update_dns_status('pending_dns', {'dns_resolved': False})
        else:
            print("✅ DNS resolving...")

            # Check full connection
            connection_ok = check_connection_completion(target_domain)
            if not connection_ok:
                print("⏳ DNS resolved but connection not complete...")
                update_dns_status('resolving', {'dns_resolved': True, 'connection_ready': False})
            else:
                print("🎉 DNS fully resolved and connection complete!")
                notify_dns_completion()
                break

        time.sleep(check_interval)


def main():
    """
    Example usage. Customize the target_domain for your specific setup.
    """
    # Example domains to monitor:
    # - ngrok: 'your-app.ngrok.io'
    # - cloudflare: 'your-app.trycloudflare.com'
    # - custom domain: 'api.yourdomain.com'

    target_domain = "example.com"  # Replace with your actual domain

    print("Alan DNS Completion Monitor")
    print("This will monitor DNS propagation and connection completion.")
    print(f"Target domain: {target_domain}")
    print("Press Ctrl+C to stop monitoring")
    print()

    try:
        dns_monitor_loop(target_domain, check_interval=30)  # Check every 30 seconds
    except KeyboardInterrupt:
        print("\nDNS monitoring stopped by user.")
    except Exception as e:
        print(f"DNS monitoring error: {e}")


if __name__ == "__main__":
    main()