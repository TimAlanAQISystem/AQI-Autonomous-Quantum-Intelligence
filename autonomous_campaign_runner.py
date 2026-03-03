"""
Autonomous Outbound Campaign Runner for Agent X (SOLID V3)
Runs continuously during business hours.
Handles all errors gracefully. Never crashes to desktop.
"""
import os
import sys
import time
import logging
import traceback
import requests
import re
import json
from datetime import datetime, time as time_type
from dotenv import load_dotenv

# Import Cooldown Manager
from tools import cooldown_manager
import agent_sql_tracker # [NEW] SQL Communication Command Center

# CW23 Regime Engine Integration
try:
    from regime_queue_integrator import (
        should_skip_lead as regime_should_skip,
        get_pacing_delay as regime_pacing,
        get_regime_summary,
        score_lead as regime_score_lead,
    )
    REGIME_AVAILABLE = True
except ImportError:
    REGIME_AVAILABLE = False

# IQcore Burn-Rate Monitoring (v3.0.0)
try:
    from iqcore_alerts import check_burn_rates as iqcore_check_burns
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False

# --- CONFIGURATION ---
LOG_FILE = "logs/autonomous_campaign.log"
POLL_INTERVAL = 15   # REVERTED to short poll (15s), effectively gated by Cooldown Manager (150s)
ERROR_SLEEP = 300   # seconds to sleep after a critical crash before retrying
HEARTBEAT_FILE = "logs/campaign_heartbeat.txt"
TUNNEL_LOG = "logs/tunnel.log"
LOCK_FILE = "logs/ALAN_SYSTEM_LOCK.lock"
# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure rigid file logging
# NOTE: logging.basicConfig is a NO-OP if the root logger already has handlers.
# agent_sql_tracker adds a StreamHandler(stderr) at import time, so we must
# force-configure the root logger by clearing existing handlers first.
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.INFO)
_fmt = logging.Formatter('%(asctime)s - [CAMPAIGN] - %(levelname)s - %(message)s')
_fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
_fh.setFormatter(_fmt)
# Wrap stdout in a UTF-8 writer to prevent UnicodeEncodeError on Windows
# when Start-Process redirects stdout to a file with cp1252 encoding.
import io
_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
_sh = logging.StreamHandler(_utf8_stdout)
_sh.setFormatter(_fmt)
root_logger.addHandler(_fh)
root_logger.addHandler(_sh)

# Load context
env_path = os.path.join(os.path.dirname(__file__), 'Alan_Deployment', 'config', '.env')
load_dotenv(env_path, override=True)

# Enforce Identity
os.environ["AGENT_NAME"] = "Alan Jones"

class SafeCampaignRunner:
    def __init__(self):
        self.running = True
        self.public_tunnel_url = os.getenv('PUBLIC_TUNNEL_URL')
        self.control_api_url = "http://127.0.0.1:8777"
        self.beta_targets = []
        self.beta_mode = False # Disable Beta Mode for Production Launch
        self.socket_error_count = 0 
        self.recent_area_codes = [] # ENTROPY INJECTION: Track last few area codes
        self.cycles_since_verification = 0 # VERITAS: Counter for Truth Audit
        logging.info("Initializing SafeCampaignRunner V3 (Governed Mode)...")
        
        # Verify Merchant Queue Import
        try:
            import merchant_queue
            self.mq = merchant_queue
            logging.info("MerchantQueue module loaded successfully.")
        except ImportError as e:
            logging.critical(f"Failed to load merchant_queue: {e}")
            self.running = False
            
    def warm_up_agent(self):
        """
        Pre-load the heavy Agent class to reduce Cold Start latency.
        """
        try:
            logging.info("[WARMUP] Warming up AgentAlanBusinessAI...")
            import agent_alan_business_ai
            # Just importing might be enough if it initializes models at module level,
            # but usually we want to instantiate once to fill caches.
            # We won't instantiate fully as that might consume a Twilio connection, 
            # but we ensure the module is in memory.
            logging.info("[WARMUP] Agent Warm-up Complete.")
        except Exception as e:
            logging.error(f"Warm-up failed: {e}")

    def is_business_hours(self):
        """Check if 9:30am - 4pm Local Time.
        [2026-03-02] Start pushed to 9:30 AM, end pulled to 4 PM — Tim: 'reduce the hours'
        """
        now = datetime.now()
        
        # WEEKEND GUARD: If user is off, Alan sleeps.
        # 5 = Saturday, 6 = Sunday
        # [KINETIC PHASE OVERRIDE]: Allow Saturday (5) for Live-Fire Exercise
        if now.weekday() == 6: # Only Block Sunday
            return False
            
        hour = now.hour
        minute = now.minute
        # Business Hours: 9:30 AM - 4:00 PM
        # [2026-03-02] Was 8am-5pm — narrowed to 9:30am-4pm for quality pacing
        if hour < 9 or (hour == 9 and minute < 30):
            return False
        if hour >= 16:
            return False
        return True

    def update_heartbeat(self):
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))

    def refresh_tunnel_url(self):
        """
        Dynamically fetch the latest tunnel URL from logs/active_tunnel_url.txt 
        or logs/tunnel.log as fallback.
        """
        try:
            # 1. Preferred Method: Explicit Active Tunnel File (ngrok/cloudflare agnostic)
            active_tunnel_file = "logs/active_tunnel_url.txt"
            if os.path.exists(active_tunnel_file):
                 # Use 'utf-8-sig' to automatically handle and remove BOM if present
                 with open(active_tunnel_file, "r", encoding="utf-8-sig") as f:
                    new_url = f.read().strip()
                     # EXTRA SANITIZATION: Remove any remaining non-printable chars just in case
                    new_url = ''.join(c for c in new_url if c.isprintable())
                    
                    if new_url:
                        if new_url != self.public_tunnel_url:
                             logging.info(f"Updated Tunnel URL from active_tunnel_url.txt: {new_url}")
                             self.public_tunnel_url = new_url
                             os.environ['PUBLIC_TUNNEL_URL'] = new_url
                        # CRITICAL FIX: Always return if we found a valid URL in the lockfile
                        # This prevents falling back to stale logs when the URL hasn't changed.
                        return

            # 2. Legacy Method: Scan tunnel.log for regex matches
            if os.path.exists(TUNNEL_LOG):
                with open(TUNNEL_LOG, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Match Cloudflare OR Ngrok
                    matches = re.findall(r"https://[a-z0-9-]+\.(?:trycloudflare\.com|ngrok-free\.dev)", content)
                    if matches:
                        new_url = matches[-1]
                        if new_url != self.public_tunnel_url:
                            logging.info(f"Updated Tunnel URL from logs: {new_url}")
                            self.public_tunnel_url = new_url
                            # Update Env for subprocesses
                            os.environ['PUBLIC_TUNNEL_URL'] = new_url
        except Exception as e:
            logging.warning(f"Tunnel refresh failed: {e}")

    def process_callback_requests(self, queue):
        """
        Reads pending callback requests and updates the merchant queue.
        """
        callback_file = "data/callback_requests.json"
        if not os.path.exists(callback_file):
            return

        try:
            with open(callback_file, 'r') as f:
                requests_list = json.load(f)
            
            if not requests_list:
                return

            updates = False
            for req in requests_list:
                if req.get("status") == "pending":
                    phone = req.get("phone_number")
                    scheduled_time_str = req.get("scheduled_time")
                    
                    if not phone or not scheduled_time_str:
                        continue
                        
                    # Normalize phone (simple check)
                    target_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                    if target_phone.startswith("+1"): target_phone = target_phone[2:]
                    
                    # Find merchant
                    # Accessing private list provided we know implementation - or iterate
                    found_merchant = None
                    # Use _merchants.values() as the public property might be missing
                    merchants_list = getattr(queue, "merchants", None) or getattr(queue, "_merchants", {}).values()
                    
                    for merchant in merchants_list: # direct access to list
                        m_phone = merchant.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                        if m_phone.startswith("+1"): m_phone = m_phone[2:]
                        
                        if m_phone == target_phone or m_phone in target_phone or target_phone in m_phone:
                            found_merchant = merchant
                            break
                    
                    if found_merchant:
                        logging.info(f"Processing Callback Request for {found_merchant.name} at {scheduled_time_str}")
                        try:
                            dt = datetime.fromisoformat(scheduled_time_str)
                            queue.update_merchant_outcome(
                                found_merchant.id, 
                                self.mq.CallOutcome.CALLBACK_SCHEDULED, # Using the new enum value
                                details=f"Requested: {req.get('request_text')}",
                                next_attempt=dt
                            )
                            req["status"] = "processed"
                            updates = True
                        except Exception as e:
                            logging.error(f"Failed to update callback for {phone}: {e}")
            
            if updates:
                with open(callback_file, 'w') as f:
                    json.dump(requests_list, f, indent=2)
                    
        except Exception as e:
            logging.error(f"Callback processing failed: {e}")

    def make_call(self, lead, queue):
        """
        Trigger the call via the Control API
        """
        try:
            logging.info(f"Initiating call to {lead.id} ({lead.phone_number})...")
            
            # --- START CRITICAL SECTION ---
            cooldown_manager.mark_call_started()
            
            try:
                payload = {
                    "to": lead.phone_number,
                    "lead_id": lead.id,
                    "lead_name": lead.name or "Merchant",
                    # [CAMPAIGN WIRING] Context Fields
                    "lead_source": getattr(lead, "lead_source", None),
                    "monthly_volume": getattr(lead, "monthly_volume", None),
                    "tier": getattr(lead, "tier", None),
                    "expected_pitch": getattr(lead, "expected_pitch", None),
                    "fallback_pitch": getattr(lead, "fallback_pitch", None),
                    
                    "campaign": "v3_solid",
                    "tunnel_url": self.public_tunnel_url,
                    # We remove 'twilio_voice_url' so control_api.py constructs it dynamically
                    # with the full context parameters appended to /twilio/voice/inbound
                    "live": True
                }
                
                # Call the local API which handles the Twilio logic
                resp = requests.post(f"{self.control_api_url}/call", json=payload, timeout=10)
                
                if resp.status_code == 200:
                    logging.info(f"Call initiated successfully: {resp.text}")
                    
                    # --- SQL TRACKING: GENESIS ---
                    try:
                        resp_json = resp.json()
                        result = resp_json.get('result', {})
                        sid = result.get('call_sid')
                        
                        if sid:
                            agent_sql_tracker.log_communication_event(sid, {
                                'merchant_name': lead.business_type or lead.name,
                                'phone_number': lead.phone_number,
                                'status': 'initiated',
                                'stealth_logic_version': 'v3.1_sql',
                                'vulture_reattempts': getattr(lead, 'attempts', 0)
                            })
                            logging.info(f"[SQL] Created communication log for {sid}")
                    except Exception as sqle:
                        logging.error(f"[SQL ERROR] Failed to create log: {sqle}")

                    # Record outcome PERSISTENTLY
                    queue.update_merchant_outcome(lead.id, self.mq.CallOutcome.CONNECTED, details="Initiated via V3 Runner")
                else:
                    logging.error(f"Call API failed: {resp.status_code} - {resp.text}")
                    queue.update_merchant_outcome(lead.id, self.mq.CallOutcome.FAILED, details=f"API Error {resp.status_code}")

            finally:
                # --- END CRITICAL SECTION ---
                # Mark ended REGARDLESS of success or crash
                cooldown_manager.mark_call_ended()
                
        except Exception as e:
            logging.error(f"Call invocation failed: {e}")
            queue.update_merchant_outcome(lead.id, self.mq.CallOutcome.FAILED, details=f"Runner Exception: {e}")

    def run_cycle(self):
        """
        The core logic of a single campaign beat.
        """
        try:
            # Reload queue module to pick up external changes/additions to the JSON
            # if "merchant_queue" in sys.modules:
            #     import importlib
            #     importlib.reload(sys.modules["merchant_queue"])
            import merchant_queue
            
            self.refresh_tunnel_url()
            
            # --- START VERITAS PROTOCOL (The Self-Diagnostic) ---
            # [2026-03-02] DISABLED: verify_truth_billing.py does not exist.
            # VERITAS was firing every cycle with exit code 2 (file not found) 
            # and spamming CRITICAL logs. Disabled until audit script is created.
            # self.cycles_since_verification += 1
            # if self.cycles_since_verification >= 20:
            #     ...
            # --- END VERITAS PROTOCOL ---

            queue = merchant_queue.MerchantQueue()
            
            # Check for and apply any scheduled callbacks from the Agent
            self.process_callback_requests(queue)
            
            # --- COOLDOWN GATE ---
            # Enforce the 150s cooldown invariant from cooldown_manager.py
            if not cooldown_manager.cooldown_gate():
                # Gate is closed. Do not proceed to lead selection.
                self.update_heartbeat()
                return    

            # --- IQCORE BURN-RATE CHECK ---
            if IQCORE_AVAILABLE:
                try:
                    burn_alerts = iqcore_check_burns()
                    for ba in burn_alerts:
                        if ba.get("level") == "CRITICAL":
                            logging.warning(f"\ud83e\udde0 [IQCORE] CRITICAL burn: {ba['actor']} at {ba['burn_pct']}%")
                except Exception:
                    pass  # IQcore monitoring is best-effort

            # --- SYSTEM LOCK CHECK (New Fail-Safe) ---
            if os.path.exists(LOCK_FILE):
                logging.warning("[LOCKED] CAMPAIGN LOCKED by Alan Zombie Hunter. Skipping cycle.")
                self.update_heartbeat()
                return

            # --- BETA MODE OVERRIDE ---
            if self.beta_mode and self.beta_targets:
                target = self.beta_targets.pop(0) # Take the first one
                logging.info(f"[BETA] BETA MODE: Targeting {target['name']} ({target['phone']})")
                
                # Create a temporary lead object compatible with the queue
                class BetaLead:
                    def __init__(self, t):
                        self.id = t['id']
                        self.phone_number = t['phone']
                        self.name = t['name']
                
                self.make_call(BetaLead(target), queue)
                
                if not self.beta_targets:
                    logging.info("[BETA] All Beta Targets processed. Switching to Auto-Pilot safely.")
                    self.beta_mode = False # Disable beta mode after list exhaustion
                    
                self.update_heartbeat()
                return # Skip normal queue this cycle

            # --- LEAD SELECTION (Standard) ---
            # ENTROPY INJECTION: Prevent calling same area code > 2 times in a row
            exclude_acs = []
            if len(self.recent_area_codes) >= 2:
                if self.recent_area_codes[-1] == self.recent_area_codes[-2]:
                    exclude_acs = [self.recent_area_codes[-1]]
                    logging.info(f"[ENTROPY] Avoiding Area Code {exclude_acs[0]} to prevent localization loops.")

            next_lead = queue.get_next_merchant(exclude_area_codes=exclude_acs)
            
            if next_lead:
                # CW23 Regime Engine: check if this lead's segment should be skipped
                if REGIME_AVAILABLE:
                    skip, skip_reason = regime_should_skip(
                        next_lead.phone_number,
                        getattr(next_lead, 'business_type', '') or ''
                    )
                    if skip:
                        logging.info(f"[REGIME SKIP] {next_lead.name} - {skip_reason}")
                        queue.update_merchant_outcome(
                            next_lead.id, self.mq.CallOutcome.FAILED,
                            details=f"Regime skip: {skip_reason}"
                        )
                        self.update_heartbeat()
                        return

                    # Log regime score for telemetry
                    score, seg_key, seg_info = regime_score_lead(
                        next_lead.phone_number,
                        getattr(next_lead, 'business_type', '') or ''
                    )
                    logging.info(f"[REGIME] {next_lead.name} -> seg={seg_key} status={seg_info.get('status','?')} score={score}")

                logging.info(f"Found eligible lead: {next_lead.name}")
                
                # Update Area Code History
                clean_phone = next_lead.phone_number.replace("+1", "").replace("(", "").replace(")", "").replace("-", "").strip()
                if len(clean_phone) >= 3:
                    ac = clean_phone[:3]
                    self.recent_area_codes.append(ac)
                    if len(self.recent_area_codes) > 5: self.recent_area_codes.pop(0)

                self.make_call(next_lead, queue)
                
                # --- VULTURE STRATEGY: AGGRESSIVE RE-DIAL ---
                # "Tries the top leads twice in a row if they don't pick up the first time"
                if hasattr(next_lead, 'priority') and next_lead.priority == "URGENT":
                    logging.info(f"[VULTURE] Monitoring {next_lead.name} for rapid re-engagement...")
                    # Short pause to allow Twilio callback to process (Avg ring time ~30s)
                    time.sleep(45) 
                    
                    # Reload snapshot from disk to check real-time outcome
                    # (The 'queue' object in memory won't have the callback update yet)
                    try:
                        check_queue = self.mq.MerchantQueue() 
                        # Access internal dict directly for speed, assuming ID matches
                        updated_lead = check_queue._merchants.get(next_lead.id)
                        
                        if updated_lead:
                            # If outcome updated to 'no_answer' or 'busy', we strike again immediately.
                            # If it's still 'connected', they are talking (Good).
                            # If it's 'failed', we might want to retry too, but 'no_answer' is the target.
                            if updated_lead.outcome in [self.mq.CallOutcome.NO_ANSWER, self.mq.CallOutcome.BUSY, self.mq.CallOutcome.FAILED]:
                                logging.info(f"[VULTURE] STRIKE: {next_lead.name} outcome was '{updated_lead.outcome.value}'. RE-DIALING IMMEDIATELY.")
                                # Force a second call packet
                                self.make_call(next_lead, queue)
                    except Exception as ve:
                        logging.error(f"Vulture logic error: {ve}")
                
                # [MECHANICS] POWER BOOST: REDUCING INTER-CALL LATENCY
                # "The crew is on the floor. The engine is screaming."
                logging.info("[POWER] High-Velocity Mode Active. Latency buffers minimized to 1.5s.")
                time.sleep(1.5) 
            else:
                logging.info("No eligible leads found (or all filtered by Entropy/Cooldown). Sleeping...")
                time.sleep(POLL_INTERVAL) 
                
            self.update_heartbeat()

        except Exception as e:
            logging.error(f"Error in run_cycle: {e}")
            logging.error(traceback.format_exc())

    def start(self):
        logging.info("Starting Main Loop...")
        self.update_heartbeat()
        self.warm_up_agent() # Run Warm-up before loop
        
        while self.running:
            try:
                if self.is_business_hours():
                    self.run_cycle()
                    time.sleep(POLL_INTERVAL)
                else:
                    # Heartbeat still updates so the monitor doesn't kill us
                    self.update_heartbeat()
                    time.sleep(3600) # Sleep an hour
            except KeyboardInterrupt:
                logging.info("Stopping via KeyboardInterrupt.")
                self.running = False
            except Exception as e:
                logging.critical(f"CRITICAL MAIN LOOP CRASH: {e}")
                logging.critical(traceback.format_exc())
                time.sleep(ERROR_SLEEP)

if __name__ == "__main__":
    runner = SafeCampaignRunner()
    runner.start()
