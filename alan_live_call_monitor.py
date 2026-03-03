"""
ALAN LIVE CALL MONITOR - ENTERPRISE GRADE
==========================================
Real-time monitoring system for live merchant calls.

Monitors:
- Merchant speech & transcripts
- Merchant tone & sentiment
- Alan's responses & quality
- Call flow validation
- Error detection & alerting
- Performance metrics

Author: Enterprise Hardening System
Date: February 3, 2026
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import re

# Sentiment Analysis
try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    logging.warning("[MONITOR] TextBlob not available - sentiment analysis disabled")

@dataclass
class CallMetrics:
    """Real-time call metrics"""
    call_sid: str
    session_id: str
    start_time: datetime
    merchant_phone: str = ""
    
    # Speech metrics
    merchant_turns: int = 0
    alan_turns: int = 0
    merchant_words: int = 0
    alan_words: int = 0
    
    # Timing metrics
    avg_response_time: float = 0.0
    last_response_time: float = 0.0
    silence_gaps: List[float] = field(default_factory=list)
    
    # Quality metrics
    merchant_sentiment: str = "neutral"
    conversation_quality: str = "good"
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)
    
    # Flow validation
    greeting_sent: bool = False
    agent_wired: bool = False
    first_merchant_response: bool = False
    conversation_active: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "call_sid": self.call_sid,
            "session_id": self.session_id,
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "merchant_turns": self.merchant_turns,
            "alan_turns": self.alan_turns,
            "merchant_words": self.merchant_words,
            "alan_words": self.alan_words,
            "avg_response_time": round(self.avg_response_time, 2),
            "merchant_sentiment": self.merchant_sentiment,
            "conversation_quality": self.conversation_quality,
            "error_count": self.error_count,
            "warnings": self.warnings,
            "flow_status": {
                "greeting_sent": self.greeting_sent,
                "agent_wired": self.agent_wired,
                "first_merchant_response": self.first_merchant_response,
                "conversation_active": self.conversation_active
            }
        }

@dataclass
class TranscriptEntry:
    """Transcript entry with metadata"""
    timestamp: datetime
    speaker: str  # "merchant" or "alan"
    text: str
    sentiment: str = "neutral"
    tone: str = "neutral"
    word_count: int = 0
    response_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "speaker": self.speaker,
            "text": self.text,
            "sentiment": self.sentiment,
            "tone": self.tone,
            "word_count": self.word_count,
            "response_time": round(self.response_time, 2)
        }

class ToneAnalyzer:
    """Analyzes tone from text"""
    
    # Tone patterns
    EXCITED_PATTERNS = [
        r"!", r"\?!", r"wow", r"great", r"awesome", r"perfect", r"love"
    ]
    
    FRUSTRATED_PATTERNS = [
        r"not interested", r"don't (want|need|have)", r"busy", r"no thanks",
        r"stop calling", r"remove me", r"already have"
    ]
    
    CURIOUS_PATTERNS = [
        r"\?", r"tell me more", r"how (does|do)", r"what (is|are)",
        r"explain", r"interested", r"sounds good"
    ]
    
    GUARDED_PATTERNS = [
        r"who (is|are) you", r"who's calling", r"how did you get",
        r"where did you", r"what company"
    ]
    
    @staticmethod
    def analyze_tone(text: str) -> str:
        """Analyze tone from text"""
        text_lower = text.lower()
        
        # Check patterns
        excited_count = sum(1 for pattern in ToneAnalyzer.EXCITED_PATTERNS 
                           if re.search(pattern, text_lower))
        frustrated_count = sum(1 for pattern in ToneAnalyzer.FRUSTRATED_PATTERNS 
                              if re.search(pattern, text_lower))
        curious_count = sum(1 for pattern in ToneAnalyzer.CURIOUS_PATTERNS 
                           if re.search(pattern, text_lower))
        guarded_count = sum(1 for pattern in ToneAnalyzer.GUARDED_PATTERNS 
                           if re.search(pattern, text_lower))
        
        # Determine dominant tone
        if frustrated_count > 0:
            return "frustrated"
        elif guarded_count > 0:
            return "guarded"
        elif excited_count > 0:
            return "excited"
        elif curious_count > 0:
            return "curious"
        else:
            return "neutral"

class SentimentAnalyzer:
    """Analyzes sentiment from text"""
    
    @staticmethod
    def analyze_sentiment(text: str) -> str:
        """Analyze sentiment from text"""
        if not SENTIMENT_AVAILABLE:
            # Fallback to basic keyword analysis
            text_lower = text.lower()
            positive_words = ["yes", "great", "good", "perfect", "interested", "sounds good", "ok"]
            negative_words = ["no", "not interested", "busy", "stop", "don't", "can't"]
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                return "positive"
            elif neg_count > pos_count:
                return "negative"
            else:
                return "neutral"
        
        # Use TextBlob for sentiment analysis
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return "positive"
            elif polarity < -0.1:
                return "negative"
            else:
                return "neutral"
        except:
            return "neutral"

class LiveCallMonitor:
    """
    Real-time call monitoring system
    Tracks all aspects of live merchant calls
    """
    
    def __init__(self):
        self.active_calls: Dict[str, CallMetrics] = {}
        self.transcripts: Dict[str, List[TranscriptEntry]] = {}
        self.alerts: deque = deque(maxlen=100)  # Last 100 alerts
        
        self.tone_analyzer = ToneAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Error patterns to detect
        self.error_patterns = [
            "error", "exception", "failed", "timeout", "disconnect",
            "unavailable", "crash", "fatal"
        ]
        
        # Quality thresholds
        self.max_silence_gap = 5.0  # seconds
        self.max_response_time = 8.0  # seconds
        self.min_merchant_engagement = 3  # minimum turns for good call
        
        logging.info("[MONITOR] 🎯 Live Call Monitor initialized")
    
    def start_call(self, call_sid: str, session_id: str, merchant_phone: str = ""):
        """Start monitoring a new call"""
        metrics = CallMetrics(
            call_sid=call_sid,
            session_id=session_id,
            start_time=datetime.now(),
            merchant_phone=merchant_phone
        )
        
        self.active_calls[call_sid] = metrics
        self.transcripts[call_sid] = []
        
        logging.info(f"[MONITOR] 📞 Started monitoring call {call_sid}")
        return metrics
    
    def log_greeting_sent(self, call_sid: str):
        """Log that greeting was sent"""
        if call_sid in self.active_calls:
            self.active_calls[call_sid].greeting_sent = True
            logging.info(f"[MONITOR] ✅ Greeting sent for {call_sid}")
    
    def log_agent_wired(self, call_sid: str):
        """Log that agent was wired"""
        if call_sid in self.active_calls:
            self.active_calls[call_sid].agent_wired = True
            logging.info(f"[MONITOR] ✅ Agent wired for {call_sid}")
    
    def log_merchant_speech(self, call_sid: str, text: str, response_time: float = 0.0):
        """Log merchant speech with analysis"""
        if call_sid not in self.active_calls:
            logging.warning(f"[MONITOR] Unknown call {call_sid}")
            return
        
        metrics = self.active_calls[call_sid]
        
        # Analyze text
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        tone = self.tone_analyzer.analyze_tone(text)
        word_count = len(text.split())
        
        # Update metrics
        metrics.merchant_turns += 1
        metrics.merchant_words += word_count
        metrics.merchant_sentiment = sentiment
        
        if not metrics.first_merchant_response:
            metrics.first_merchant_response = True
            logging.info(f"[MONITOR] 🎤 First merchant response in {call_sid}")
        
        # Create transcript entry
        entry = TranscriptEntry(
            timestamp=datetime.now(),
            speaker="merchant",
            text=text,
            sentiment=sentiment,
            tone=tone,
            word_count=word_count,
            response_time=response_time
        )
        
        self.transcripts[call_sid].append(entry)
        
        # Log analysis
        logging.info(
            f"[MONITOR] 🎤 Merchant [{call_sid[:8]}]: "
            f"'{text[:50]}...' | Tone: {tone} | Sentiment: {sentiment}"
        )
        
        # Check for alerts
        self._check_merchant_alerts(call_sid, text, tone, sentiment)
    
    def log_alan_response(self, call_sid: str, text: str, response_time: float = 0.0):
        """Log Alan's response with analysis"""
        if call_sid not in self.active_calls:
            logging.warning(f"[MONITOR] Unknown call {call_sid}")
            return
        
        metrics = self.active_calls[call_sid]
        
        # Analyze text
        word_count = len(text.split())
        
        # Update metrics
        metrics.alan_turns += 1
        metrics.alan_words += word_count
        
        # Update response time
        if response_time > 0:
            if metrics.avg_response_time == 0:
                metrics.avg_response_time = response_time
            else:
                metrics.avg_response_time = (metrics.avg_response_time + response_time) / 2
            
            metrics.last_response_time = response_time
        
        # Create transcript entry
        entry = TranscriptEntry(
            timestamp=datetime.now(),
            speaker="alan",
            text=text,
            word_count=word_count,
            response_time=response_time
        )
        
        self.transcripts[call_sid].append(entry)
        
        # Log response
        logging.info(
            f"[MONITOR] 💬 Alan [{call_sid[:8]}]: "
            f"'{text[:50]}...' | Words: {word_count} | Response: {response_time:.2f}s"
        )
        
        # Check for quality issues
        self._check_alan_quality(call_sid, text, response_time)
    
    def log_error(self, call_sid: str, error_type: str, error_message: str):
        """Log an error during the call"""
        if call_sid in self.active_calls:
            metrics = self.active_calls[call_sid]
            metrics.error_count += 1
            
            alert = {
                "timestamp": datetime.now().isoformat(),
                "call_sid": call_sid,
                "type": "ERROR",
                "error_type": error_type,
                "message": error_message
            }
            
            self.alerts.append(alert)
            
            logging.error(
                f"[MONITOR] ❌ ERROR in {call_sid[:8]}: {error_type} - {error_message}"
            )
    
    def log_warning(self, call_sid: str, warning_message: str):
        """Log a warning during the call"""
        if call_sid in self.active_calls:
            metrics = self.active_calls[call_sid]
            metrics.warnings.append(warning_message)
            
            alert = {
                "timestamp": datetime.now().isoformat(),
                "call_sid": call_sid,
                "type": "WARNING",
                "message": warning_message
            }
            
            self.alerts.append(alert)
            
            logging.warning(f"[MONITOR] ⚠️ WARNING in {call_sid[:8]}: {warning_message}")
    
    def end_call(self, call_sid: str):
        """End monitoring for a call"""
        if call_sid not in self.active_calls:
            return
        
        metrics = self.active_calls[call_sid]
        metrics.conversation_active = False
        
        # Calculate final quality score
        quality = self._calculate_call_quality(call_sid)
        metrics.conversation_quality = quality
        
        # Log summary
        duration = (datetime.now() - metrics.start_time).total_seconds()
        
        logging.info(
            f"\n[MONITOR] 📊 CALL SUMMARY [{call_sid[:8]}]:\n"
            f"  Duration: {duration:.1f}s\n"
            f"  Merchant Turns: {metrics.merchant_turns}\n"
            f"  Alan Turns: {metrics.alan_turns}\n"
            f"  Merchant Sentiment: {metrics.merchant_sentiment}\n"
            f"  Quality: {quality}\n"
            f"  Errors: {metrics.error_count}\n"
            f"  Avg Response Time: {metrics.avg_response_time:.2f}s"
        )
        
        # Save transcript
        self._save_transcript(call_sid)
    
    def get_call_metrics(self, call_sid: str) -> Optional[Dict]:
        """Get current metrics for a call"""
        if call_sid in self.active_calls:
            return self.active_calls[call_sid].to_dict()
        return None
    
    def get_active_calls(self) -> List[Dict]:
        """Get all active calls"""
        return [
            metrics.to_dict()
            for metrics in self.active_calls.values()
            if metrics.conversation_active
        ]
    
    def get_transcript(self, call_sid: str) -> List[Dict]:
        """Get transcript for a call"""
        if call_sid in self.transcripts:
            return [entry.to_dict() for entry in self.transcripts[call_sid]]
        return []
    
    def get_recent_alerts(self, count: int = 20) -> List[Dict]:
        """Get recent alerts"""
        return list(self.alerts)[-count:]
    
    def _check_merchant_alerts(self, call_sid: str, text: str, tone: str, sentiment: str):
        """Check for merchant-related alerts"""
        text_lower = text.lower()
        
        # Check for negative sentiment
        if sentiment == "negative" and tone == "frustrated":
            self.log_warning(
                call_sid,
                f"Merchant frustrated: '{text[:50]}...'"
            )
        
        # Check for hang-up indicators
        hangup_phrases = [
            "not interested", "don't call", "stop calling",
            "remove me", "take me off", "goodbye"
        ]
        
        if any(phrase in text_lower for phrase in hangup_phrases):
            self.log_warning(
                call_sid,
                f"Potential hang-up: '{text[:50]}...'"
            )
        
        # Check for confusion
        confusion_phrases = [
            "what", "who is this", "i don't understand",
            "confused", "what are you talking about"
        ]
        
        if any(phrase in text_lower for phrase in confusion_phrases):
            self.log_warning(
                call_sid,
                f"Merchant confused: '{text[:50]}...'"
            )
    
    def _check_alan_quality(self, call_sid: str, text: str, response_time: float):
        """Check Alan's response quality"""
        # Check response time
        if response_time > self.max_response_time:
            self.log_warning(
                call_sid,
                f"Slow response: {response_time:.2f}s (threshold: {self.max_response_time}s)"
            )
        
        # Check for very short responses
        word_count = len(text.split())
        if word_count < 3:
            self.log_warning(
                call_sid,
                f"Very short response: only {word_count} words"
            )
        
        # Check for repetition
        if call_sid in self.transcripts:
            recent_alan_responses = [
                entry.text for entry in self.transcripts[call_sid][-5:]
                if entry.speaker == "alan"
            ]
            
            if len(recent_alan_responses) >= 2 and text in recent_alan_responses[:-1]:
                self.log_warning(
                    call_sid,
                    f"Repetitive response detected: '{text[:30]}...'"
                )
    
    def _calculate_call_quality(self, call_sid: str) -> str:
        """Calculate overall call quality"""
        if call_sid not in self.active_calls:
            return "unknown"
        
        metrics = self.active_calls[call_sid]
        
        # Quality factors
        score = 100
        
        # Check flow completion
        if not metrics.greeting_sent:
            score -= 30
        if not metrics.agent_wired:
            score -= 30
        if not metrics.first_merchant_response:
            score -= 20
        
        # Check engagement
        if metrics.merchant_turns < self.min_merchant_engagement:
            score -= 15
        
        # Check errors
        score -= metrics.error_count * 10
        
        # Check warnings
        score -= len(metrics.warnings) * 5
        
        # Check sentiment
        if metrics.merchant_sentiment == "negative":
            score -= 10
        
        # Determine quality
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "fair"
        else:
            return "poor"
    
    def _save_transcript(self, call_sid: str):
        """Save transcript to file"""
        if call_sid not in self.transcripts:
            return
        
        try:
            transcript_dir = Path("logs/call_transcripts")
            transcript_dir.mkdir(parents=True, exist_ok=True)
            
            filename = transcript_dir / f"transcript_{call_sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            data = {
                "call_sid": call_sid,
                "metrics": self.active_calls[call_sid].to_dict() if call_sid in self.active_calls else {},
                "transcript": self.get_transcript(call_sid)
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"[MONITOR] 💾 Transcript saved: {filename}")
            
        except Exception as e:
            logging.error(f"[MONITOR] Failed to save transcript: {e}")

# Global monitor instance
live_monitor = LiveCallMonitor()

# Convenience functions for easy integration
def start_monitoring(call_sid: str, session_id: str, merchant_phone: str = ""):
    """Start monitoring a call"""
    return live_monitor.start_call(call_sid, session_id, merchant_phone)

def log_greeting(call_sid: str):
    """Log greeting sent"""
    live_monitor.log_greeting_sent(call_sid)

def log_agent_ready(call_sid: str):
    """Log agent wired"""
    live_monitor.log_agent_wired(call_sid)

def log_merchant(call_sid: str, text: str, response_time: float = 0.0):
    """Log merchant speech"""
    live_monitor.log_merchant_speech(call_sid, text, response_time)

def log_alan(call_sid: str, text: str, response_time: float = 0.0):
    """Log Alan's response"""
    live_monitor.log_alan_response(call_sid, text, response_time)

def log_call_error(call_sid: str, error_type: str, error_message: str):
    """Log call error"""
    live_monitor.log_error(call_sid, error_type, error_message)

def log_call_warning(call_sid: str, warning: str):
    """Log call warning"""
    live_monitor.log_warning(call_sid, warning)

def end_monitoring(call_sid: str):
    """End call monitoring"""
    live_monitor.end_call(call_sid)

def get_active_calls():
    """Get all active calls"""
    return live_monitor.get_active_calls()

def get_call_status(call_sid: str):
    """Get call status"""
    return live_monitor.get_call_metrics(call_sid)

def get_call_transcript(call_sid: str):
    """Get call transcript"""
    return live_monitor.get_transcript(call_sid)

def get_alerts(count: int = 20):
    """Get recent alerts"""
    return live_monitor.get_recent_alerts(count)

if __name__ == "__main__":
    # Test the monitor
    print("🎯 Alan Live Call Monitor - Test Mode\n")
    
    test_call = "CA_TEST_12345"
    test_session = "session_test_001"
    
    # Start monitoring
    start_monitoring(test_call, test_session, "+14062102346")
    log_greeting(test_call)
    log_agent_ready(test_call)
    
    # Simulate conversation
    log_alan(test_call, "Hey, this is Alan Jones with Signature Card Services out in Chicago.", 3.2)
    log_merchant(test_call, "Hello? Who is this?", 0.8)
    log_alan(test_call, "It's Alan - I'm looking at the interchange rates for restaurants in your area.", 2.1)
    log_merchant(test_call, "Oh okay. What about them?", 1.2)
    log_alan(test_call, "I think you might be paying the convenience tax. You got thirty seconds for the math?", 2.5)
    log_merchant(test_call, "Yeah sure, tell me more.", 0.9)
    
    # End monitoring
    end_monitoring(test_call)
    
    # Display results
    print("\n📊 Call Metrics:")
    print(json.dumps(get_call_status(test_call), indent=2))
    
    print("\n📝 Transcript:")
    for entry in get_call_transcript(test_call):
        speaker = "🎤 MERCHANT" if entry["speaker"] == "merchant" else "💬 ALAN"
        print(f"{speaker}: {entry['text']} (Sentiment: {entry['sentiment']})")
