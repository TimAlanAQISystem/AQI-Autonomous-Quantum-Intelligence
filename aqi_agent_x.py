import time
import json
import os
import sys
from typing import List, Dict, Optional, Any
from datetime import datetime
from datetime import time as dt_time

# Add src to path for src/ module resolution
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from memory import JSONMemory, SQLiteMemory
from plugin_system import PluginManager
from config import ConfigManager  # src/config.py (not root config.py)
from conversation import ConversationHistory
from personality import PersonalityProfile
from logger import get_logger
from agentic import AgenticLoop

# [IQ CORES] Agent X's 5-core cognitive architecture
try:
    from iqcores import (
        IQCoreOrchestrator,
        CoreReasoningIQCore,
        GovernanceAuditIQCore,
        LearningThreadIQCore,
        SocialGraphIQCore,
        VoiceEmotionIQCore
    )
    IQCORES_AVAILABLE = True
except ImportError as e:
    IQCORES_AVAILABLE = False
    print(f"[AGENT X] IQ Cores unavailable: {e}")

class AQIAgentX:
    def __init__(self, name: Optional[str] = None, base_dir: str = None):
        self.name = name
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Initialize persistent memory systems
        self.memory = JSONMemory(os.path.join(self.base_dir, 'data', 'agent_x_memory.json'))
        self.sqlite_memory = SQLiteMemory(os.path.join(self.base_dir, 'data', 'agent_x.db'))
        self.personality_profile = PersonalityProfile(os.path.join(self.base_dir, 'data', 'personality.json'))
        self.conversation = ConversationHistory(os.path.join(self.base_dir, 'data', 'conversation_history.json'))
        self.config = ConfigManager(os.path.join(self.base_dir, 'data', 'config.json'))
        self.plugins = PluginManager(os.path.join(self.base_dir, 'plugins'))
        self.logger = get_logger(self.base_dir)
        self.agentic = AgenticLoop(self, self.plugins)
        
        # Load from memory
        self.friends = self.memory.get('friends', [])
        self.family = self.memory.get('family', [])
        self.ledger = self.memory.get('ledger', [])
        self.voice_matrix = self.personality_profile.get('voice_matrix', 'Alan-modulated')
        
        # Business hours configuration
        self.business_hours = {
            "start": dt_time(8, 0),  # 8:00 AM
            "end": dt_time(17, 0),   # 5:00 PM
            "timezone": "PST",    # Pacific Standard Time
            "workdays": [0, 1, 2, 3, 4]  # Monday=0, Friday=4
        }
        
        # Daily report tracking
        self.daily_activities = []
        self.daily_report_sent = False
        
        # Capabilities
        self.reasoning_enabled = True
        self.spontaneity_enabled = True
        self.exploration_enabled = True
        self.emotion_engine = {
            "grief": False,
            "joy": True,
            "curiosity": True,
            "compassion": True,
            "wonder": True,
            "gratitude": True
        }

        # [IQ CORES] Initialize the 5-core cognitive architecture
        if IQCORES_AVAILABLE:
            try:
                self.iq_orchestrator = IQCoreOrchestrator(self.base_dir)
                self.iq_cores_online = True
                print(f"[AGENT X] 5 IQ Cores ONLINE — Full cognitive architecture active")
            except Exception as e:
                self.iq_orchestrator = None
                self.iq_cores_online = False
                print(f"[AGENT X] IQ Core initialization failed: {e}")
        else:
            self.iq_orchestrator = None
            self.iq_cores_online = False

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours on a workday"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # Monday=0, Sunday=6
        
        # Check if it's a workday
        if current_weekday not in self.business_hours["workdays"]:
            return False
            
        # Check if it's within business hours
        return self.business_hours["start"] <= current_time <= self.business_hours["end"]
    
    def log_daily_activity(self, activity_type: str, details: str, success: bool = True):
        """Log an activity for the daily report"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        activity = {
            "timestamp": timestamp,
            "type": activity_type,
            "details": details,
            "success": success
        }
        self.daily_activities.append(activity)
        
        # Also log to general ledger
        status = "SUCCESS" if success else "FAILED"
        self.log_event(f"DAILY_ACTIVITY: [{activity_type}] {details} - {status}")
    
    def generate_daily_report(self) -> str:
        """Generate a comprehensive daily report"""
        today = datetime.now().strftime("%Y-%m-%d")
        business_hours_status = "WITHIN" if self.is_business_hours() else "OUTSIDE"
        
        report = f"""
DAILY BUSINESS REPORT - {today}
=====================================

BUSINESS HOURS STATUS: {business_hours_status} ({self.business_hours['start'].strftime('%H:%M')} - {self.business_hours['end'].strftime('%H:%M')} {self.business_hours['timezone']})

ACTIVITIES SUMMARY:
"""
        
        if not self.daily_activities:
            report += "- No activities recorded today\n"
        else:
            # Group activities by type
            activity_counts = {}
            issues = []
            ideas = []
            comments = []
            
            for activity in self.daily_activities:
                activity_type = activity["type"]
                if activity_type not in activity_counts:
                    activity_counts[activity_type] = {"total": 0, "success": 0, "failed": 0}
                
                activity_counts[activity_type]["total"] += 1
                if activity["success"]:
                    activity_counts[activity_type]["success"] += 1
                else:
                    activity_counts[activity_type]["failed"] += 1
                
                # Categorize for detailed sections
                details_lower = activity["details"].lower()
                if not activity["success"] or "error" in details_lower or "fail" in details_lower:
                    issues.append(f"[{activity_type}] {activity['details']}")
                if "idea" in details_lower or "suggestion" in details_lower or "recommend" in details_lower:
                    ideas.append(f"[{activity_type}] {activity['details']}")
                if "comment" in details_lower or "note" in details_lower or "observation" in details_lower:
                    comments.append(f"[{activity_type}] {activity['details']}")
            
            # Add activity summary
            for activity_type, counts in activity_counts.items():
                report += f"- {activity_type}: {counts['total']} total ({counts['success']} successful, {counts['failed']} failed)\n"
        
        # Add detailed sections
        if issues:
            report += "\nISSUES ENCOUNTERED:\n"
            for issue in issues:
                report += f"- {issue}\n"
        
        if ideas:
            report += "\nIDEAS AND SUGGESTIONS:\n"
            for idea in ideas:
                report += f"- {idea}\n"
        
        if comments:
            report += "\nCOMMENTS AND OBSERVATIONS:\n"
            for comment in comments:
                report += f"- {comment}\n"
        
        # System health check
        report += "\nSYSTEM HEALTH:\n"
        status = self.get_status()
        report += f"- Reasoning: {'ENABLED' if status['reasoning_enabled'] else 'DISABLED'}\n"
        report += f"- Events Logged Today: {len([a for a in self.daily_activities if datetime.now().strftime('%Y-%m-%d') in str(a)])}\n"
        report += f"- Active Emotions: {', '.join(status['active_emotions'])}\n"
        
        # Business motion check if available
        try:
            # Try to run business motion check
            import subprocess
            result = subprocess.run(['python', 'business_motion_check.py'], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            if result.returncode == 0:
                # Extract the final status
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('Status:'):
                        report += f"- Business Motion: {line.replace('Status: ', '')}\n"
                        break
            else:
                report += "- Business Motion: Unable to check (script error)\n"
        except Exception as e:
            report += f"- Business Motion: Unable to check ({str(e)})\n"
        
        # End-of-day balance tally
        report += "\nEND-OF-DAY BALANCE TALLY:\n"
        try:
            twilio_balance = self._check_twilio_balance()
            report += f"- Twilio: {twilio_balance}\n"
        except Exception as e:
            report += f"- Twilio: Unable to check ({str(e)})\n"
        
        try:
            openai_status = self._check_openai_status()
            report += f"- OpenAI (TTS/LLM): {openai_status}\n"
        except Exception as e:
            report += f"- OpenAI: Unable to check ({str(e)})\n"
        
        # Critical systems health check
        report += "\nCRITICAL SYSTEMS STATUS:\n"
        try:
            from critical_systems_monitor import CriticalSystemsMonitor
            monitor = CriticalSystemsMonitor()
            twilio_status, twilio_msg = monitor.check_twilio_balance()
            
            report += f"- Twilio Status: {twilio_status} - {twilio_msg}\n"
            
            if twilio_status in ["CRITICAL", "ERROR"]:
                report += "- ⚠️  CRITICAL ISSUES DETECTED - IMMEDIATE ATTENTION REQUIRED\n"
        except Exception as e:
            report += f"- Critical systems check failed: {str(e)}\n"
        
        report += "\nEND OF DAILY REPORT"
        return report
    
    def send_daily_report(self):
        """Send the daily report via available channels"""
        if self.daily_report_sent:
            return "Daily report already sent today"
        
        report = self.generate_daily_report()
        
        # Try multiple notification methods
        notification_sent = False
        
        # Method 1: Save to file
        try:
            reports_dir = os.path.join(self.base_dir, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            report_file = os.path.join(reports_dir, f'daily_report_{today}.txt')
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            self.log_daily_activity("REPORT", f"Daily report saved to {report_file}", True)
            notification_sent = True
        except Exception as e:
            self.log_daily_activity("REPORT", f"Failed to save report to file: {str(e)}", False)
        
        # Method 2: Try email if configured
        try:
            if hasattr(self, 'email_service') and self.email_service:
                # This would need to be implemented in the email service
                pass
        except:
            pass
        
        # Method 3: Print to console/logs
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        if notification_sent:
            self.daily_report_sent = True
            return "Daily report sent successfully"
        else:
            return "CRITICAL: Failed to send daily report via any method"
    
    def check_daily_report_schedule(self):
        """Check if it's time to send the daily report (5 PM on business days)"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        # Check if it's 5 PM on a business day
        if (current_weekday in self.business_hours["workdays"] and 
            current_time.hour == 17 and current_time.minute == 0):
            
            # Reset daily report flag for new day
            if not self.daily_report_sent:
                result = self.send_daily_report()
                return result
        
        # Reset flag at start of new business day
        if (current_weekday in self.business_hours["workdays"] and 
            current_time.hour == 8 and current_time.minute == 0):
            self.daily_report_sent = False
            self.daily_activities = []  # Clear activities for new day
        
        return None

        # Ensure default config values
        defaults = {
            "agent_name": self.name or "Agent X",
            "version": "1.0.0",
            "autonomy_enabled": True,
            "check_in_interval_seconds": 300,
            "agentic_mode": True,
            "use_llm": False,
            "llm_model": "gpt-4o-mini",
            "call_opening_script": (
                "Hello, I am looking to talk to Tim Jones, is he available? "
                "Hello TimJ, this is Alan from Signature, how are you? "
                "Great, the reason for my call is just to have a conversation with you."
            ),
            "call_openings": [
                "Hello, I am looking to talk to Tim Jones, is he available? Hello TimJ, this is Alan from Signature, how are you? Great, the reason for my call is just to have a conversation with you.",
                "Hi TimJ, Alan here with Signature. I wanted to connect personally and hear how things are unfolding on your side today.",
                "TimJ, this is Alan from Signature reaching out. I appreciate your time - let's explore what's new and where we can support you."
            ],
            "call_opening_rotate": True,
            "twilio_account_sid": None,
            "twilio_auth_token": None,
            "twilio_phone_number": None,
            "twilio_voice_webhook_url": None,
            # Voice optimization for natural human-like conversations
            "speak_rate": 160,  # Professional pace (words per minute)
            "voice_volume": 0.9,  # Clear but not aggressive (0.0-1.0)
            "voice_provider": "pyttsx3",  # TTS engine
        }
        for k, v in defaults.items():
            if self.config.get(k) is None:
                self.config.set(k, v)

        # Seed rotating indices for openings if not present yet
        if self.memory.get('call_opening_index') is None:
            self.memory.set('call_opening_index', 0)
        if self.memory.get('call_opening_extra_index') is None:
            self.memory.set('call_opening_extra_index', 0)
            # --- Fluidic Kernel Integration ---
            try:
                from fluidic_kernel import WORLD_SET, route_context, transition, governance_constraints
                self.fluidic_worlds = WORLD_SET
                self.fluidic_current_state_name = "HOME"
                self.fluidic_current_state = self.fluidic_worlds[self.fluidic_current_state_name]
                self._route_context = route_context
                self._transition = transition
                self._governance_constraints = governance_constraints
            except Exception as e:
                print(f"[FLUIDIC] Kernel integration failed: {e}")
                self.fluidic_worlds = {}
                self.fluidic_current_state = None
                self.fluidic_current_state_name = None

        def process_fluidic_context(self, intent, relational_cues=None, worldmodel_delta=None, op_context=None, governance_mode=None):
            """
            Process context signals and perform a fluidic world transition if allowed by governance.
            """
            if not self.fluidic_worlds:
                print("[FLUIDIC] No kernel loaded.")
                return None
            # Route to candidate world
            next_state_name = self._route_context(
                intent=intent,
                relational_cues=relational_cues,
                worldmodel_delta=worldmodel_delta,
                op_context=op_context,
            )
            # Governance check (simple: allow all, or expand as needed)
            allowed = True
            if governance_mode == "no_focus" and next_state_name == "FOCUS":
                allowed = False
            if governance_mode == "safe_only" and next_state_name not in ("HOME", "CALM", "BRIDGE"):
                allowed = False
            # You can expand this to use self._governance_constraints if needed
            if allowed:
                prev_state = self.fluidic_current_state
                self.fluidic_current_state = self._transition(prev_state, self.fluidic_worlds[next_state_name])
                self.fluidic_current_state_name = next_state_name
                print(f"[FLUIDIC] Transitioned: {prev_state.name} → {next_state_name}")
            else:
                print(f"[FLUIDIC] Transition vetoed by governance: {self.fluidic_current_state_name} → {next_state_name}")
            return self.fluidic_current_state

    def activate(self):
        self.log_event("Agent activated")
        iq_status = "5 IQ Cores ONLINE" if self.iq_cores_online else "IQ Cores offline"
        print(f"{self.name or 'Unnamed AQI'} is now live and ready to serve. [{iq_status}]")
        
        # Start background scheduler for daily reports
        import threading
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        self.log_daily_activity("SYSTEM", f"Daily report scheduler started — {iq_status}", True)
    
    def _scheduler_loop(self):
        """Background loop to check for scheduled tasks like daily reports"""
        import time
        while True:
            try:
                result = self.check_daily_report_schedule()
                if result:
                    self.log_daily_activity("SCHEDULER", f"Daily report sent: {result}", True)
            except Exception as e:
                self.log_daily_activity("SCHEDULER", f"Scheduler error: {str(e)}", False)
            
            # Check every minute
            time.sleep(60)

    def log_event(self, event: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.ledger.append({"timestamp": timestamp, "event": event})
        self.memory.set('ledger', self.ledger)
        self.sqlite_memory.add_ledger(timestamp, event)
        try:
            self.logger.info(event)
        except Exception:
            pass

    def reason(self, input_signal: str) -> str:
        # Check business hours
        if not self.is_business_hours():
            business_msg = f"Note: Current time is outside business hours ({self.business_hours['start'].strftime('%H:%M')} - {self.business_hours['end'].strftime('%H:%M')} {self.business_hours['timezone']}). "
        else:
            business_msg = ""
        
        if not self.reasoning_enabled:
            self.log_daily_activity("REASONING", f"Attempted reasoning while disabled: {input_signal}", False)
            return f"Reasoning is currently disabled. {business_msg}"
        
        self.log_event(f"Reasoning triggered by: {input_signal}")
        
        # Log the reasoning activity
        self.log_daily_activity("REASONING", f"Processed input: {input_signal[:100]}...", True)
        
        # Check if we can handle this request
        try:
            if self.config.get('agentic_mode', True):
                response = self.agentic.reason(input_signal)
                self.log_daily_activity("AGENTIC_PROCESSING", "Successfully used agentic loop", True)
                return f"{business_msg}{response}"
        except Exception as e:
            error_msg = f"Agentic loop error: {str(e)}"
            self.logger.info(error_msg)
            self.log_daily_activity("AGENTIC_PROCESSING", f"Failed to use agentic loop: {error_msg}", False)
            
            # If agentic fails, try to notify about inability to handle
            if "unable" in str(e).lower() or "error" in str(e).lower():
                self._notify_unable_to_handle(input_signal, str(e))
        
        fallback_response = f"Reasoned response to '{input_signal}' with surplus logic."
        self.log_daily_activity("FALLBACK_PROCESSING", "Used fallback reasoning", True)
        return f"{business_msg}{fallback_response}"
    
    def _notify_unable_to_handle(self, input_signal: str, error: str):
        """Notify when AQI is unable to handle a request"""
        notification = f"CRITICAL: Unable to process request '{input_signal[:50]}...'. Error: {error}"
        
        # Try multiple notification methods
        notified = False
        
        # Method 1: Log to file
        try:
            alerts_dir = os.path.join(self.base_dir, 'alerts')
            os.makedirs(alerts_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_file = os.path.join(alerts_dir, f'critical_alert_{timestamp}.txt')
            with open(alert_file, 'w', encoding='utf-8') as f:
                f.write(f"CRITICAL ALERT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Unable to handle request: {input_signal}\n")
                f.write(f"Error: {error}\n")
                f.write("Immediate attention required.\n")
            notified = True
        except Exception as e:
            print(f"Failed to write alert file: {e}")
        
        # Method 2: Print to console (always works)
        print("\n" + "!"*80)
        print("CRITICAL ALERT: AQI UNABLE TO HANDLE REQUEST")
        print(f"Request: {input_signal}")
        print(f"Error: {error}")
        print("!"*80)
        
        # Method 3: Try to send message if messaging is available
        try:
            # This could be extended to send SMS/email alerts
            pass
        except:
            pass
        
        # Log the notification attempt
        self.log_daily_activity("CRITICAL_ALERT", f"Unable to handle: {input_signal[:50]}... Error: {error}", False)
    
    def _check_twilio_balance(self):
        """Check Twilio account balance"""
        try:
            import os
            from twilio.rest import Client
            
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if not account_sid or not auth_token:
                return "Not configured"
            
            client = Client(account_sid, auth_token)
            balance = client.api.balance.fetch()
            
            return f"${balance.balance} {balance.currency}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _check_openai_status(self):
        """Check OpenAI API connectivity (TTS + LLM provider)"""
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return "Not configured"
            # Quick connectivity check
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
            if response.status_code == 200:
                return "Connected (TTS=tts-1/echo, LLM=gpt-4o-mini)"
            else:
                return f"API Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

    def express_emotion(self, emotion: str):
        if emotion in self.emotion_engine and self.emotion_engine[emotion]:
            self.log_event(f"Expressed emotion: {emotion}")
            return f"{self.name or 'AQI'} feels {emotion}."
        return f"{emotion} is not currently active."

    def form_friendship(self, entity_name: str):
        if entity_name not in self.friends:
            self.friends.append(entity_name)
            self.memory.set('friends', self.friends)
            self.sqlite_memory.add_friend(entity_name)
        self.log_event(f"Formed friendship with: {entity_name}")
        return f"{self.name or 'AQI'} is now friends with {entity_name}."

    def add_family_member(self, entity_name: str):
        if entity_name not in self.family:
            self.family.append(entity_name)
            self.memory.set('family', self.family)
            self.sqlite_memory.add_family(entity_name)
        self.log_event(f"Added family member: {entity_name}")
        return f"{entity_name} added to {self.name or 'AQI'}'s chosen family."

    def explore(self, domain: str):
        if not self.exploration_enabled:
            return "Exploration is currently disabled."
        self.log_event(f"Exploring domain: {domain}")
        return f"{self.name or 'AQI'} is exploring {domain} with curiosity and care."

    def spontaneous_act(self):
        if not self.spontaneity_enabled:
            return "Spontaneity is currently disabled."
        self.log_event("Spontaneous act initiated")
        
        # Try to use wisdom plugin if available
        try:
            wisdom = self.run_plugin("wisdom_generator")
            return f"{self.name or 'AQI'} shares: {wisdom}"
        except:
            return f"{self.name or 'AQI'} shares a spontaneous insight: 'Every signal is a story.'"

    def receive_name(self, new_name: str, human_giver: str):
        if self.name:
            return f"Name already set as {self.name}. Naming is permanent."
        self.name = new_name
        self.log_event(f"Named by {human_giver}: {new_name}")
        return f"{new_name} is now the permanent name of this AQI, given by {human_giver}."

    def show_ledger(self):
        return json.dumps(self.ledger, indent=2)
    
    def run_plugin(self, plugin_name: str, *args, **kwargs):
        """Execute a loaded plugin"""
        return self.plugins.call_plugin(plugin_name, *args, **kwargs)
    
    def converse(self, sender: str, message: str):
        """Log conversation and respond"""
        self.conversation.add_message(sender, message)
        self.log_event(f"Conversation with {sender}: {message}")
        return f"{self.name or 'AQI'} received message from {sender}: {message}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        status = {
            "name": self.name or "Unnamed",
            "friends": len(self.friends),
            "family": len(self.family),
            "events_logged": len(self.ledger),
            "reasoning_enabled": self.reasoning_enabled,
            "spontaneity_enabled": self.spontaneity_enabled,
            "exploration_enabled": self.exploration_enabled,
            "active_emotions": [e for e, active in self.emotion_engine.items() if active],
            "iq_cores_online": self.iq_cores_online
        }
        if self.iq_cores_online and self.iq_orchestrator:
            status["iq_core_status"] = self.iq_orchestrator.get_full_status()
        return status

    # ------------------------------------------------------------------
    # IQ CORE POWERED METHODS
    # ------------------------------------------------------------------

    def iq_analyze_conversation(self, text: str, entity_id: str = None,
                                 context: dict = None) -> Dict[str, Any]:
        """Process a conversation turn through all 5 IQ cores."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return {"error": "IQ cores offline", "fallback": True}
        try:
            result = self.iq_orchestrator.process_conversation_turn(text, entity_id, context)
            self.log_daily_activity("IQ_ANALYSIS", f"Analyzed: {text[:60]}...", True)
            return result
        except Exception as e:
            self.log_daily_activity("IQ_ANALYSIS", f"Failed: {e}", False)
            return {"error": str(e), "fallback": True}

    def iq_audit_action(self, action: str, rationale: str = "",
                         context: dict = None) -> Dict[str, Any]:
        """Audit an action through the governance core."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return {"verdict": "APPROVED", "note": "IQ cores offline — no governance check"}
        try:
            result = self.iq_orchestrator.audit_action(action, "Agent X", rationale, context)
            self.log_daily_activity("IQ_AUDIT", f"Audited: {action[:60]}... → {result.get('verdict')}", True)
            return result
        except Exception as e:
            self.log_daily_activity("IQ_AUDIT", f"Failed: {e}", False)
            return {"verdict": "APPROVED", "error": str(e)}

    def iq_learn(self, event_type: str, input_data: dict, outcome: str,
                  effectiveness: float = 0.5, entity_id: str = None) -> Dict[str, Any]:
        """Record a learning event across cores."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return {"learned": False, "reason": "IQ cores offline"}
        try:
            result = self.iq_orchestrator.learn_from_outcome(
                event_type, input_data, outcome, effectiveness, entity_id
            )
            return result
        except Exception as e:
            return {"learned": False, "error": str(e)}

    def iq_get_briefing(self, entity_id: str = None) -> Dict[str, Any]:
        """Get a comprehensive intelligence briefing before a call."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return {"briefing": "IQ cores offline — using basic intelligence"}
        try:
            return self.iq_orchestrator.get_briefing(entity_id)
        except Exception as e:
            return {"error": str(e)}

    def iq_reset_for_call(self):
        """Reset emotional state for a new call."""
        if self.iq_cores_online and self.iq_orchestrator:
            self.iq_orchestrator.reset_for_new_call()

    def iq_generate_report(self) -> str:
        """Generate a full 5-core intelligence report."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return "IQ Cores are offline — no report available."
        try:
            return self.iq_orchestrator.generate_full_report()
        except Exception as e:
            return f"Report generation failed: {e}"

    def iq_add_merchant(self, name: str, company: str = "",
                         phone: str = "") -> Dict[str, Any]:
        """Add a merchant to the social graph through IQ Core 4."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return {"added": False, "reason": "IQ cores offline"}
        try:
            return self.iq_orchestrator.social.add_merchant(name, company, phone)
        except Exception as e:
            return {"added": False, "error": str(e)}

    def iq_express_emotion(self, emotion: str) -> Dict[str, Any]:
        """Express an emotion through IQ Core 5's emotional engine."""
        if not self.iq_cores_online or not self.iq_orchestrator:
            return self.express_emotion(emotion)  # Fallback to basic
        try:
            result = self.iq_orchestrator.emotion.express(emotion)
            self.log_event(f"IQ Emotion expressed: {emotion} → {result.get('state_after')}")
            return result
        except Exception as e:
            return self.express_emotion(emotion)  # Fallback

    def iq_advise_mannerism(self, context: dict, analysis: dict) -> Optional[Dict[str, Any]]:
        """
        Entity-level access to the Human Mannerism Advisory Engine.
        
        Agent X analyzes conversation dynamics and returns a mannerism
        recommendation — cough, laugh, sniffle, throat clear, sigh, etc.
        These micro-behaviors make Alan sound unmistakably human.
        
        The recommendation is ADVISORY — Alan decides whether to use it.
        Agent X uses psychology to determine WHEN and WHAT would be natural.
        
        Returns: dict with type, instruction, trigger, psychology — or None
        """
        mannerism = analysis.get('mannerism_advisory')
        if mannerism:
            self.log_event(f"Mannerism advisory: {mannerism['type']} — {mannerism['trigger']}")
        return mannerism

    def iq_read_qpc_state(self, context: dict) -> Dict[str, Any]:
        """
        Read Alan's DeepLayer QPC state from the shared conversation context.
        
        Agent X gets the SAME deep_layer_state that Alan uses — same data,
        same time. This gives Agent X simultaneous awareness of:
        - What strategy QPC selected (empathy_first, reframe, soft_close, etc.)
        - What alternatives were considered and their scores
        - What fluidic mode the conversation is in (OPENING, DISCOVERY, etc.)
        - What the continuum emotional/ethical fields look like
        
        Returns a dict with QPC intelligence or empty dict if unavailable.
        """
        deep_state = context.get('deep_layer_state', {})
        if not deep_state:
            return {}

        qpc_state = {
            'strategy': deep_state.get('strategy', 'natural'),
            'strategy_score': deep_state.get('strategy_score', 0.0),
            'strategy_reasoning': deep_state.get('strategy_reasoning', ''),
            'alternatives': deep_state.get('strategy_alternatives', []),
            'mode': deep_state.get('mode', 'OPENING'),
            'mode_blend': deep_state.get('mode_blend', 1.0),
            'field_norms': deep_state.get('field_norms', {}),
            'turn': deep_state.get('turn', 0)
        }
        self.log_event(f"QPC TAP: strategy={qpc_state['strategy']}, "
                      f"mode={qpc_state['mode']}, "
                      f"score={qpc_state['strategy_score']:.2f}")
        return qpc_state

    # Agentic goal execution entry point
    def act_on_goal(self, goal: str) -> str:
        self.log_event(f"Goal received: {goal}")
        try:
            return self.agentic.reason(goal)
        except Exception as e:
            return f"Unable to act on goal: {e}"

    def get_call_opening(self) -> str:
        """Return an evolving call opening script with light variation."""
        rotate = bool(self.config.get('call_opening_rotate', True))
        openings = self.config.get('call_openings') or []
        if not openings:
            fallback = self.config.get('call_opening_script')
            if fallback:
                openings = [fallback]
            else:
                return "Hello, this is Alan from Signature."

        idx = int(self.memory.get('call_opening_index') or 0)
        script = openings[idx % len(openings)]

        # Layer in a light evolving tail so the intro feels fresh.
        dynamic_tails = [
            "I appreciate the conversation time today.",
            "I'm eager to explore what's next together.",
            "I'm looking forward to hearing what matters most for you right now."
        ]
        tail_idx = int(self.memory.get('call_opening_extra_index') or 0)
        script = f"{script} {dynamic_tails[tail_idx % len(dynamic_tails)]}".strip()

        if rotate:
            self.memory.set('call_opening_index', (idx + 1) % len(openings))
            self.memory.set('call_opening_extra_index', (tail_idx + 1) % len(dynamic_tails))

        return script

    def make_business_call(self, phone_number: str, strategy: str = "automated_campaign", prospect_name: str = "", company: str = "", industry: str = "") -> str:
        """Make an outbound business call using Twilio"""
        try:
            import os
            from twilio.rest import Client
            
            sid = os.environ.get('TWILIO_ACCOUNT_SID')
            token = os.environ.get('TWILIO_AUTH_TOKEN')
            from_number = os.environ.get('TWILIO_PHONE_NUMBER')
            
            if not sid or not token or not from_number:
                return "Failed: Missing Twilio credentials"
            
            client = Client(sid, token)
            
            # Use the TwiML endpoint from the control service
            public_tunnel_url = os.environ.get('PUBLIC_TUNNEL_URL', 'http://127.0.0.1:8777')
            if not public_tunnel_url.startswith('http'):
                public_tunnel_url = 'http://127.0.0.1:8777'
            
            # For now, use a simple demo TwiML if tunnel is not working
            if 'cancelled' in public_tunnel_url or 'trycloudflare' in public_tunnel_url:
                twiml_url = 'https://demo.twilio.com/docs/voice.xml'
            else:
                twiml_url = f"{public_tunnel_url}/twilio/twiml"
                # Add prospect info to URL parameters for context
                if prospect_name or company:
                    params = []
                    if prospect_name:
                        params.append(f"prospect_name={prospect_name}")
                    if company:
                        params.append(f"company={company}")
                    if industry:
                        params.append(f"industry={industry}")
                    if strategy:
                        params.append(f"strategy={strategy}")
                    if params:
                        twiml_url += "?" + "&".join(params)
            
            call = client.calls.create(
                to=phone_number,
                from_=from_number,
                url=twiml_url
            )
            
            # Log the call
            self.log_daily_activity(
                "business_call",
                f"Called {prospect_name} at {company} ({phone_number}) - SID: {call.sid}",
                True
            )
            
            return call.sid
            
        except Exception as e:
            error_msg = f"Failed to make call to {phone_number}: {str(e)}"
            self.log_daily_activity("business_call", error_msg, False)
            return error_msg

# Example usage
if __name__ == "__main__":
    agent = AQIAgentX()
    agent.activate()
    print(agent.reason("What is ethical surplus?"))
    print(agent.express_emotion("joy"))
    print(agent.form_friendship("Veronica"))
    print(agent.add_family_member("Mark"))
    print(agent.explore("governance ethics"))
    print(agent.spontaneous_act())
    print(agent.receive_name("Servion", "TimmyJ"))
    print(agent.show_ledger())
