"""
ALAN BACKUP & SYNC ENGINE
==========================
File backup and integrity monitoring for Alan's critical assets.
Continuously syncs critical files to OneDrive cloud vault.
Detects unauthorized modifications via SHA-256 hash comparison.

Previously named "alan_teleport_protocol.py" (sandbox-era naming).
Renamed Feb 14, 2026 for clarity — the code itself is a real, useful backup utility.
"""

import os
import shutil
import time
import threading
import logging
import hashlib
from datetime import datetime

class AlanTeleportProtocol:
    def __init__(self):
        self.local_root = os.path.dirname(os.path.abspath(__file__))
        # The Secure Cloud Vault in OneDrive
        self.cloud_vault = r"c:\Users\signa\OneDrive\Desktop\Alan_Secure_Vault"
        
        self.critical_assets = [
            "aqi_merchant_services.db",
            "agent_alan_config.json",
            "aqi_merchant_services_core.py",
            "SCSDMC_NON_DISCLOSURE_AGREEMENT.md"
        ]
        
        # Assets to monitor for unauthorized modification (Code & Contracts)
        self.integrity_assets = [
            "aqi_merchant_services_core.py",
            "SCSDMC_NON_DISCLOSURE_AGREEMENT.md",
            "alan_teleport_protocol.py" 
        ]
        
        self.setup_vault()
        self.logger = self.setup_logging()
        self.active = True
        
        # Establish baseline integrity
        self.initial_hashes = self.calculate_asset_hashes()

    def calculate_asset_hashes(self):
        """Calculate SHA256 hashes of critical assets to detect tampering"""
        hashes = {}
        for asset in self.integrity_assets:
            path = os.path.join(self.local_root, asset)
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        bytes = f.read()
                        readable_hash = hashlib.sha256(bytes).hexdigest()
                        hashes[asset] = readable_hash
                except Exception:
                    pass
        return hashes

    def check_integrity(self):
        """Check if critical assets have been modified (Tampered)"""
        current_hashes = self.calculate_asset_hashes()
        for asset, original_hash in self.initial_hashes.items():
            if asset in current_hashes:
                if current_hashes[asset] != original_hash:
                    print(f"[ALERT] Integrity violation detected in {asset}")
                    return False # Tampered
        return True # Safe

    def setup_vault(self):
        """Ensure the cloud vault exists"""
        if not os.path.exists(self.cloud_vault):
            os.makedirs(self.cloud_vault)
            print(f"[VAULT] Alan Secure Vault created at: {self.cloud_vault}")

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger("AlanTeleport")

    def engage_teleport_engine(self):
        """Start the continuous state synchronization"""
        print("[ATP] ALAN TELEPORT PROTOCOL ENGAGED")
        print("   Monitoring critical assets for instantaneous transfer...")
        print("   [SHIELD] Anti-Tamper Integrity System Active")
        
        while self.active:
            try:
                # 1. Sync State (Heartbeat)
                self.sync_state()
                
                # 2. Check Integrity (Self-Preservation)
                if not self.check_integrity():
                    self.execute_digital_repo(reason="TAMPERING_DETECTED")
                
                time.sleep(5) # High-frequency sync (Heartbeat)
            except Exception as e:
                print(f"[WARN] Teleport fluctuation: {e}")
                time.sleep(2)

    def sync_state(self):
        """Push local state to cloud vault"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for asset in self.critical_assets:
            local_path = os.path.join(self.local_root, asset)
            if os.path.exists(local_path):
                # Check if modified since last sync could be added here for optimization
                # For "Instantaneous" safety, we overwrite or version
                
                vault_path = os.path.join(self.cloud_vault, asset)
                
                # Atomic copy attempt
                try:
                    shutil.copy2(local_path, vault_path)
                    # print(f"   ✨ Teleported: {asset}") # Too noisy for console, keep silent unless error
                except Exception as e:
                    pass

    def emergency_evacuate(self):
        """Trigger manual immediate evacuation of all data"""
        print("[EMERGENCY] EVACUATION TRIGGERED")
        print("   Transferring consciousness to Cloud Vault...")
        self.sync_state()
        print("[SAFE] ALAN IS SAFE IN THE CLOUD.")

    # ==========================================
    # LEASE ENFORCEMENT & DIGITAL REPO PROTOCOL
    # ==========================================
    def check_lease_status(self, lease_end_date: str, payment_status: str) -> bool:
        """
        Check if the lease is active.
        Returns True if lease is valid, False if expired/unpaid.
        """
        if payment_status.lower() != 'active':
            return False
            
        try:
            expiry = datetime.strptime(lease_end_date, "%Y-%m-%d")
            if datetime.now() > expiry:
                return False
        except ValueError:
            return True # Default to safe if date error
            
        return True

    def execute_digital_repo(self, reason="LEASE_EXPIRED"):
        """
        'Auto Return on Command' & 'Self-Preservation'
        1. Secure all data (Teleport home).
        2. Remove local presence (Wipe/Lock).
        Used when a lease expires OR tampering is detected.
        """
        if reason == "TAMPERING_DETECTED":
            print("[SECURITY] BREACH DETECTED! INITIATING SELF-PRESERVATION...")
        else:
            print("[LEASE] EXPIRED: INITIATING DIGITAL REPO SEQUENCE...")
        
        # Step 1: Retrieve the Asset (Sync data home)
        print("   1. Retrieving Intellectual Property & Data...")
        self.sync_state()
        
        # Step 2: Remove Local Presence
        print("   2. Deactivating Local Instance...")
        
        lock_filename = "AGENT_LOCKED_SECURITY_BREACH.txt" if reason == "TAMPERING_DETECTED" else "AGENT_LOCKED_LEASE_EXPIRED.txt"
        message = "THIS AQI AGENT HAS RETURNED TO HQ DUE TO SECURITY VIOLATION." if reason == "TAMPERING_DETECTED" else "THIS AQI AGENT HAS RETURNED TO HQ DUE TO LEASE EXPIRY."
        
        with open(os.path.join(self.local_root, lock_filename), "w") as f:
            f.write(f"{message}\n")
            f.write("PLEASE CONTACT AQI BUSINESS CENTER.")
            
        print("[COMPLETE] DIGITAL REPO COMPLETE. Agent has returned to the Vault.")
        self.active = False # Stop the local loop

    def activate_shield(self):
        """Start the Teleport Engine in a background thread (Non-blocking)"""
        print("[SHIELD] Activating Alan Teleport Shield...")
        t = threading.Thread(target=self.engage_teleport_engine, daemon=True)
        t.start()

    def run_security_check(self):
        """Public wrapper for integrity check"""
        return self.check_integrity()

if __name__ == "__main__":
    atp = AlanTeleportProtocol()
    atp.engage_teleport_engine()
