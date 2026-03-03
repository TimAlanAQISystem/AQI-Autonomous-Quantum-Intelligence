"""
AQI REDUNDANCY MANAGER
======================
Ensures System Survival when Primary Keys (OpenAI, Twilio) fail.
Provides "Safe Mode" and "Lobotomy Mode" fallbacks.
"""

import os
import time
import requests
import logging
from datetime import datetime

class AQIRedundancyManager:
    def __init__(self):
        self.status = {
            "openai": "unknown",
            "twilio": "unknown",
            "internet": "unknown"
        }
        self.backup_keys = {
            "openai": [],
            "twilio": []
        }
        self._load_backup_keys()
        
    def _load_backup_keys(self):
        """Load backup keys from secure storage or environment"""
        # In a real deployment, these might come from a separate encrypted vault
        # For now, we check for specific backup env vars
        if os.environ.get("OPENAI_API_KEY_BACKUP"):
            self.backup_keys["openai"].append(os.environ.get("OPENAI_API_KEY_BACKUP"))
            
        if os.environ.get("TWILIO_ACCOUNT_SID_BACKUP") and os.environ.get("TWILIO_AUTH_TOKEN_BACKUP"):
            self.backup_keys["twilio"].append({
                "sid": os.environ.get("TWILIO_ACCOUNT_SID_BACKUP"),
                "token": os.environ.get("TWILIO_AUTH_TOKEN_BACKUP")
            })

    def check_vital_signs(self):
        """Run a full system health check"""
        print("RUNNING SYSTEM VITAL SIGNS CHECK...")
        
        # 1. Check Internet
        try:
            requests.get("https://www.google.com", timeout=3)
            self.status["internet"] = "online"
            print("   [OK] Internet: ONLINE")
        except:
            self.status["internet"] = "offline"
            print("   [FAIL] Internet: OFFLINE")
            return False # Critical failure

        # 2. Check OpenAI
        if self._check_openai():
            self.status["openai"] = "operational"
            print("   [OK] Brain (OpenAI): OPERATIONAL")
        else:
            self.status["openai"] = "failed"
            print("   [FAIL] Brain (OpenAI): FAILED (Switching to Lobotomy Mode)")

        # 3. Check Twilio
        if self._check_twilio():
            self.status["twilio"] = "operational"
            print("   [OK] Voice (Twilio): OPERATIONAL")
        else:
            self.status["twilio"] = "failed"
            print("   [FAIL] Voice (Twilio): FAILED (Switching to Text-Only Mode)")
            
        return True

    def _check_openai(self):
        """Verify OpenAI connectivity"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False
        
        try:
            # Simple lightweight call to check validity
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def _check_twilio(self):
        """Verify Twilio connectivity"""
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            return False
            
        try:
            # Simple call to fetch account details
            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
            response = requests.get(url, auth=(sid, token), timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_brain_state(self):
        """Return current brain capability"""
        if self.status["openai"] == "operational":
            return "FULL_AI"
        return "LOBOTOMY_MODE" # Scripted fallback

    def get_voice_state(self):
        """Return current voice capability"""
        if self.status["twilio"] == "operational":
            return "ACTIVE_VOICE"
        return "TEXT_ONLY" # Email/Log fallback

    def activate_emergency_fallback(self, service):
        """Attempt to switch to backup credentials"""
        print(f"[WARN] ACTIVATING EMERGENCY FALLBACK FOR {service.upper()}...")
        
        if service == "openai":
            if self.backup_keys["openai"]:
                new_key = self.backup_keys["openai"].pop(0)
                os.environ["OPENAI_API_KEY"] = new_key
                print("   🔄 Switched to Backup OpenAI Key")
                return self._check_openai()
            else:
                print("   ❌ No Backup OpenAI Keys available.")
                return False
                
        if service == "twilio":
            if self.backup_keys["twilio"]:
                creds = self.backup_keys["twilio"].pop(0)
                os.environ["TWILIO_ACCOUNT_SID"] = creds["sid"]
                os.environ["TWILIO_AUTH_TOKEN"] = creds["token"]
                print("   🔄 Switched to Backup Twilio Account")
                return self._check_twilio()
            else:
                print("   ❌ No Backup Twilio Accounts available.")
                return False

        return False

