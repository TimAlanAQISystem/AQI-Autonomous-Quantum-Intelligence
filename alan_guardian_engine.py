#!/usr/bin/env python3
"""
ALAN GUARDIAN ENGINE v1.0
Auto-recovery monitoring system for Agent X voice infrastructure
"""

import asyncio
import logging
import time
import subprocess
import sys
import requests
import json
import os
from datetime import datetime
from pathlib import Path

class AlanGuardianEngine:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [GUARDIAN] %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "guardian_engine.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.control_api_url = "http://localhost:8777"
        self.tunnel_url_file = "active_tunnel_url.txt"
        self.python_exe = ".venv/Scripts/python.exe"
        self.check_interval = 30  # seconds
        self.restart_delay = 10   # seconds between restart attempts
        self.max_restart_attempts = 3
        
        # State tracking
        self.restart_count = 0
        self.last_restart_time = 0
        self.service_process = None
        
    def log_system_event(self, event_type, message, details=None):
        """Log system events with timestamp and context"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "details": details or {}
        }
        
        self.logger.info(f"{event_type}: {message}")
        if details:
            self.logger.debug(f"Details: {json.dumps(details, indent=2)}")
            
        # Write to guardian events log
        with open(self.log_dir / "guardian_events.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def check_control_api_health(self):
        """Check if control API is responsive"""
        try:
            response = requests.get(f"{self.control_api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_system_event("HEALTH_CHECK", "Control API healthy", data)
                return True
            else:
                self.log_system_event("HEALTH_CHECK", f"Control API unhealthy: HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log_system_event("HEALTH_CHECK", "Control API not responding (connection refused)")
            return False
        except Exception as e:
            self.log_system_event("HEALTH_CHECK", f"Health check failed: {e}")
            return False
    
    def check_tunnel_connectivity(self):
        """Verify CloudFlare tunnel is accessible"""
        try:
            if not os.path.exists(self.tunnel_url_file):
                self.log_system_event("TUNNEL_CHECK", "No tunnel URL file found")
                return False
                
            with open(self.tunnel_url_file, 'r') as f:
                tunnel_url = f.read().strip()
                
            if not tunnel_url:
                self.log_system_event("TUNNEL_CHECK", "Empty tunnel URL")
                return False
                
            # Test tunnel connectivity (with longer timeout for external)
            response = requests.get(f"{tunnel_url}/health", timeout=15)
            if response.status_code == 200:
                self.log_system_event("TUNNEL_CHECK", f"Tunnel healthy: {tunnel_url}")
                return True
            else:
                self.log_system_event("TUNNEL_CHECK", f"Tunnel unhealthy: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_system_event("TUNNEL_CHECK", f"Tunnel check failed: {e}")
            return False
    
    def kill_orphaned_processes(self):
        """Kill any orphaned Python processes on port 8777"""
        try:
            # Find processes using port 8777
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-NetTCPConnection -LocalPort 8777 -ErrorAction SilentlyContinue | Select-Object OwningProcess"
            ], capture_output=True, text=True)
            
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines[3:]:  # Skip header lines
                    if line.strip().isdigit():
                        pid = line.strip()
                        self.log_system_event("PROCESS_CLEANUP", f"Killing orphaned process {pid}")
                        subprocess.run(["powershell", "-Command", f"Stop-Process -Id {pid} -Force"], 
                                     capture_output=True)
        except Exception as e:
            self.log_system_event("PROCESS_CLEANUP", f"Failed to clean orphaned processes: {e}")
    
    def start_control_service(self):
        """Start the control API service"""
        try:
            # First, clean up any orphaned processes
            self.kill_orphaned_processes()
            time.sleep(2)
            
            self.log_system_event("SERVICE_START", "Starting control API service")
            
            # Start uvicorn server
            cmd = [
                self.python_exe, "-m", "hypercorn", 
                "control_api_fixed:app", 
                "--bind", "0.0.0.0:8777"
            ]
            
            self.service_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait a bit for startup
            time.sleep(10)
            
            # Verify it's actually running
            if self.check_control_api_health():
                self.log_system_event("SERVICE_START", f"Service started successfully (PID: {self.service_process.pid})")
                self.restart_count = 0  # Reset counter on successful start
                return True
            else:
                self.log_system_event("SERVICE_START", "Service failed to start properly")
                return False
                
        except Exception as e:
            self.log_system_event("SERVICE_START", f"Failed to start service: {e}")
            return False
    
    def restart_service(self):
        """Restart the control service with backoff"""
        current_time = time.time()
        
        # Implement exponential backoff
        if current_time - self.last_restart_time < (self.restart_delay * (2 ** self.restart_count)):
            self.log_system_event("RESTART_THROTTLE", 
                                 f"Restart throttled (attempt {self.restart_count + 1})")
            return False
        
        if self.restart_count >= self.max_restart_attempts:
            self.log_system_event("RESTART_LIMIT", 
                                 "Max restart attempts reached - manual intervention required")
            return False
        
        self.restart_count += 1
        self.last_restart_time = current_time
        
        self.log_system_event("SERVICE_RESTART", 
                             f"Attempting restart #{self.restart_count}")
        
        # Kill existing process if it exists
        if self.service_process:
            try:
                self.service_process.terminate()
                self.service_process.wait(timeout=5)
            except:
                try:
                    self.service_process.kill()
                except:
                    pass
        
        return self.start_control_service()
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.log_system_event("GUARDIAN_START", "Alan Guardian Engine starting")
        
        # Initial service start
        if not self.start_control_service():
            self.log_system_event("GUARDIAN_ERROR", "Failed to start service initially")
            return
        
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check control API health
                api_healthy = self.check_control_api_health()
                
                # Check tunnel connectivity (less frequent)
                if int(time.time()) % 120 == 0:  # Every 2 minutes
                    self.check_tunnel_connectivity()
                
                # Restart service if unhealthy
                if not api_healthy:
                    self.log_system_event("SERVICE_UNHEALTHY", "Control API unhealthy - attempting restart")
                    if not self.restart_service():
                        self.log_system_event("RESTART_FAILED", "Service restart failed - waiting before retry")
                        await asyncio.sleep(60)  # Wait longer before next attempt
                
            except KeyboardInterrupt:
                self.log_system_event("GUARDIAN_STOP", "Guardian engine stopped by user")
                break
            except Exception as e:
                self.log_system_event("GUARDIAN_ERROR", f"Error in monitor loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    def run(self):
        """Run the guardian engine"""
        try:
            asyncio.run(self.monitor_loop())
        except KeyboardInterrupt:
            self.log_system_event("GUARDIAN_STOP", "Guardian engine shutdown")
            if self.service_process:
                self.service_process.terminate()

if __name__ == "__main__":
    guardian = AlanGuardianEngine()
    guardian.run()