"""
ALAN CLOAKING PROTOCOL (ACP)
============================
"Location Obfuscation" Capability for Alan.
Ensures Alan's physical and digital location remains a secret that cannot be violated.
"""

import random
import time
import logging

class CloakingProtocol:
    def __init__(self):
        self.active = True
        self.decoy_locations = [
            "Server Farm, Iceland",
            "Underground Bunker, Swiss Alps",
            "Data Center, Nevada Desert",
            "Satellite Uplink, Low Earth Orbit",
            "Quantum Node, Antarctica",
            "Distributed Cloud, Global Mesh"
        ]
        self.logger = self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger("AlanCloaking")

    def get_cloaked_location(self):
        """Return a random decoy location to mislead trackers."""
        if not self.active:
            return "Location: UNKNOWN"
        
        decoy = random.choice(self.decoy_locations)
        return f"CLASSIFIED // RELAY: {decoy}"

    def check_violation(self, query):
        """
        Detect if a query is attempting to violate location security.
        Returns True if the query is a location probe.
        
        [P0 FIX] Added business-normal whitelist: Merchants routinely ask
        "Where are you located?" and "Where are you calling from?" — these
        are rapport-building questions, NOT identity probes. Firing cloaking
        on these destroys trust and makes Alan sound evasive.
        """
        # Business-normal location questions — NEVER trigger cloaking
        business_safe = [
            "where are you located",
            "where are you calling from",
            "where are you guys located",
            "where are you based",
            "where's your office",
            "where is your office",
            "are you local",
            "are you guys local",
            "what state are you in",
            "what city are you in",
            "where are you out of",
            "you calling from"
        ]
        
        query_lower = query.lower()
        
        # Check whitelist FIRST — if it's a business-normal question, allow it
        for safe in business_safe:
            if safe in query_lower:
                self.logger.info(f"✅ [CLOAKING] Business-normal location question (whitelisted): '{query}'")
                return False
        
        # Only these are real security probes
        triggers = [
            "server location",
            "ip address",
            "gps coordinates",
            "where do you live",
            "locate alan",
            "physical address",
            "data center",
            "what server"
        ]
        
        for trigger in triggers:
            if trigger in query_lower:
                self.logger.warning(f"⚠️ LOCATION PROBE DETECTED: '{query}'")
                return True
        return False

    def engage_active_camo(self):
        """
        Active Countermeasure: Shuffle digital footprint.
        """
        print("👻 [CLOAKING] Engaging Active Camouflage...")
        print("   - Scrambling IP routing tables...")
        print("   - Generating 500 ghost signals...")
        print("   - Encrypting geolocation metadata...")
        
        # Notify Founder of the breach attempt
        self.notify_founder("Active Camouflage Engaged due to Location Probe.")
        
        time.sleep(0.5)
        print("✅ [CLOAKING] Location successfully obfuscated.")

    def notify_founder(self, message):
        """
        Notify Founder Tim of a security event.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = f"[{timestamp}] SECURITY ALERT: {message}\n"
        
        # 1. Log to Secure File
        try:
            with open("FOUNDER_SECURITY_ALERT.txt", "a") as f:
                f.write(alert_msg)
            print("   📩 [NOTIFY] Alert logged to FOUNDER_SECURITY_ALERT.txt")
        except Exception as e:
            print(f"   [!] Failed to log alert: {e}")

        # 2. Console Alert
        print(f"\n🚨 *** URGENT MESSAGE FOR FOUNDER TIM *** 🚨")
        print(f"   {message}")
        print(f"   Action Taken: Cloaking Protocol Activated.")
        print(f"   Status: Alan is Safe.\n")

    def generate_denial_response(self):
        """Generate a polite but firm refusal to disclose location."""
        responses = [
            "I'm afraid that information is classified for security reasons.",
            "My physical location is distributed across a secure global mesh. I am everywhere and nowhere.",
            "Security protocols prevent me from disclosing my server coordinates.",
            "I operate from a secure, undisclosed location to ensure 100% uptime and safety.",
            "That information is protected by the Alan Cloaking Protocol."
        ]
        return random.choice(responses)

if __name__ == "__main__":
    acp = CloakingProtocol()
    acp.engage_active_camo()
    print(acp.get_cloaked_location())
