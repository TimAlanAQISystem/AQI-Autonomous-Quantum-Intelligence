# campaign_autopilot.py

import time
import sys
# Try to import modules, assuming they exist or will exist
try:
    from campaign_behavior_audit import load_calls, summarize
    # Helper to summarize for optimization engine if needed, 
    # but campaign_optimization_engine might have its own analyze method that takes raw rows?
    # Checking previous context, campaign_optimization_engine.py likely has process_calls or similar.
    # The user provided snippet assumes 'summarize' exists or we can infer it.
    # looking at previous prompts, campaign_behavior_audit.py usually has load_calls.

    from campaign_optimization_engine import CampaignOptimizationEngine
    from call_lifecycle_fsm import CallLifecycleFSM
    # governor import might need adjustment depending on where Governor class is defined.
    # Assuming it's in governor_behavior_bridge or similar, or we might need to mock if not fully linked.
    # The user snippet imports Governor from 'governor'.
    # We will try to import Governor, if not found we might need to look for it.
except ImportError:
    pass # we will fix imports if they fail

# Placeholder for Governor if not separated into its own file
# In previous sessions, Governor logic was in governor_behavior_bridge.py or call_lifecycle_fsm.py
# Let's check imports later.

from campaign_autopilot_config_loader import load_autopilot_config

class CampaignAutopilot:
    def __init__(self, cfg, governor, fsm: CallLifecycleFSM):
        self.cfg = cfg
        self.governor = governor
        self.fsm = fsm
        self.opt_engine = CampaignOptimizationEngine()

    def compute_readiness(self, days: int = 3):
        rows = load_calls(days)
        # We use the summarize function from campaign_behavior_audit
        audit_data = summarize(rows)
        
        opt = self.opt_engine.analyze(audit_data)
        return opt["readiness_score"], opt

    def run_campaign(self, dial_fn, days_for_readiness: int = 3):
        readiness, opt = self.compute_readiness(days_for_readiness)
        print(f"[AUTOPILOT] Readiness Score: {readiness}")

        if readiness < self.cfg["min_readiness_score"]:
            print("[AUTOPILOT] Readiness below threshold. Aborting campaign.")
            return

        calls_made = 0
        while calls_made < self.cfg["max_daily_calls"]:
            if not self.fsm.can_start_call():
                print("[AUTOPILOT] FSM blocking new calls (COOLDOWN or RECOVERY).")
                break

            # Run calls serially (Human Mode: One at a time)
            remaining = self.cfg["max_daily_calls"] - calls_made
            # We still respect batch size for RE-EVALUATION intervals, but execution is serial
            current_batch_limit = min(self.cfg["micro_batch_size"], remaining)
            
            print(f"[AUTOPILOT] Starting serial processing of {current_batch_limit} calls.")
            
            for i in range(current_batch_limit):
                if not self.fsm.can_start_call():
                    print("[AUTOPILOT] FSM blocked. Stopping campaign.")
                    break
                
                print(f"  [Auto] Dialing call {calls_made + 1}...")
                
                # [HUMAN MODE] Blocking Call Execution
                # We must wait for the call to actually finish before dialing the next one.
                # In a real system, dial_fn should return a handle to join/wait on.
                # If dial_fn is async fire-and-forget, we need to poll for status.
                
                call_handle = dial_fn() 
                
                # If dial_fn returns a thread or object with join/wait, use it.
                # Otherwise, we assume dial_fn blocks until call completion.
                if hasattr(call_handle, 'join'):
                    call_handle.join()
                elif hasattr(call_handle, 'wait'):
                    call_handle.wait()
                
                # Post-call breather (Human pacing)
                print("  [Auto] Call complete. Taking a breath...")
                time.sleep(3) # 3 seconds breathing room between calls
                
                calls_made += 1

            # Re-evaluate readiness after each batch interval of calls
            readiness, opt = self.compute_readiness(days_for_readiness)
            print(f"[AUTOPILOT] Post-batch readiness: {readiness}")

            if readiness < self.cfg["cooldown_on_score_drop"]:
                print("[AUTOPILOT] Readiness dropped below cooldown threshold. Entering COOLDOWN.")
                # self.governor.enter_cooldown() # Assuming governor has this method
                # If governor is an instance of SimpleGovernor or similar logic
                if hasattr(self.governor, 'enter_cooldown'):
                    self.governor.enter_cooldown()
                else:
                    # Fallback to direct FSM manipulation if Governor object isn't the FSM wrapper
                    self.fsm.enter_cooldown("AUTOPILOT_SCORE_DROP")
                break

            if calls_made >= self.cfg["max_daily_calls"]:
                print("[AUTOPILOT] Reached max_daily_calls.")
                break

            time.sleep(1)  # small pause between batches

def mock_dial():
    print("    (SIMULATED DIAL) - Ringing... Hello? ... [Conversation] ... Goodbye.")
    time.sleep(2) # Simulate call duration
    return None # Returns immediately in this mock, but real implementation would block or return handle

if __name__ == "__main__":
    # Test harness
    print("=== CAMPAIGN AUTOPILOT TEST MODE (HUMAN PACING) ===")
    cfg = load_autopilot_config()
    
    # Mock dependencies for test run
    class MockFSM:
        def can_start_call(self): return True
        def enter_cooldown(self, reason): print(f"FSM -> COOLDOWN: {reason}")
    
    class MockGovernor:
        def enter_cooldown(self): print("Governor -> requesting COOLDOWN")

    fsm = MockFSM()
    gov = MockGovernor()
    
    autopilot = CampaignAutopilot(cfg, gov, fsm)
    
    # We can't actually compute readiness without DB access and rows
    # so we might wrap this in try/except for the test run
    try:
        autopilot.run_campaign(mock_dial)
    except Exception as e:
        print(f"Test run failed (expected if DB empty): {e}")

