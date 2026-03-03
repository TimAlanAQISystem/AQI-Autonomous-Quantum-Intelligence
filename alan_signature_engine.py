# =============================================================================
# ORGAN 11 — SIGNATURE EXTRACTION & ADAPTIVE VOICE IDENTITY
# =============================================================================
# Alan's living acoustic signature — learned from real human interaction.
#
# This module does ONE thing: Learn how humans converse and use those
# patterns to shape Alan's delivery. Not copying voices. Not cloning.
# Not impersonating. Learning *patterns*.
#
# Architecture:
#   1. EXTRACTION — Pull timing/rhythm/cadence from caller speech (per-call)
#   2. LEARNING   — EMA-blend into a stable global signature (cross-call)
#   3. BIASING    — Feed signature as parameter offsets into Organs 7-10
#
# Safety:
#   - No raw audio storage
#   - No voiceprint reconstruction
#   - No caller identity linkage
#   - No timbre mimicry — only timing, rhythm, and pattern
#
# The result: Alan develops a conversational style the way humans do —
# by being shaped by the people he talks to.
# =============================================================================

import json
import os
import time
import re
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("AlanSignature")

# =============================================================================
# CONSTANTS — Safety Rails & Drift Limits
# =============================================================================

# How far global signature can drift from baseline (±%)
MAX_SPEECH_RATE_DRIFT = 0.15          # ±15% from designed baseline
MAX_PAUSE_DRIFT = 0.20               # ±20% on pause profile
MAX_BREATH_RATIO_DRIFT = 0.25        # ±25% on breath-to-speech ratio
MAX_FILLER_DRIFT = 0.30              # ±30% on filler frequency
MAX_TURN_LATENCY_DRIFT = 0.20        # ±20% on turn latency target

# EMA blending weight for global signature updates
GLOBAL_EMA_WEIGHT = 0.02             # 2% per qualifying call — slow evolution
LOCAL_BLEND_WEIGHT = 0.30            # 30% caller influence on this call

# Minimum call duration (seconds) to qualify for signature update
MIN_CALL_DURATION_FOR_UPDATE = 180   # 3 minutes — short calls don't update

# Filler words recognized in STT output
FILLER_WORDS = frozenset({
    "uh", "um", "uhm", "hmm", "mm", "mmm", "mhm", "uh-huh",
    "well", "so", "like", "you know", "i mean", "basically",
    "actually", "right", "okay"
})

# Intonation markers (from punctuation/word patterns)
RISING_MARKERS = frozenset({"?", "right?", "huh?", "yeah?"})
FALLING_MARKERS = frozenset({".", "absolutely.", "definitely.", "exactly."})

# Signature state file
SIGNATURE_STATE_FILE = "alan_signature_state.json"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SignatureSample:
    """Per-call acoustic pattern extraction. No PII. No audio. No identity."""
    
    # Speech rate (estimated syllables/sec from word count & duration)
    avg_speech_rate: float = 3.5              # Default human avg: ~3.5 syl/sec
    
    # Pause distribution: histogram buckets (count of pauses in each range)
    pauses_120_200ms: int = 0                  # Quick micro-pauses
    pauses_200_350ms: int = 0                  # Natural thought pauses
    pauses_350_600ms: int = 0                  # Deliberate/emotional pauses
    pauses_600ms_plus: int = 0                 # Long pauses (thinking/hesitation)
    
    # Breath-to-speech ratio (pause time / speech time)
    breath_to_speech_ratio: float = 0.15       # ~15% is typical
    
    # Filler frequency (fillers per minute of caller speech)
    filler_frequency: float = 2.0              # ~2/min is average
    
    # Turn latency (seconds from Alan stop → caller start)
    avg_turn_latency: float = 0.45             # ~450ms is typical
    
    # Intonation tendency (positive = rising, negative = falling, 0 = balanced)
    intonation_tendency: float = 0.0           # -1.0 to +1.0
    
    # Emotional arc shape
    emotional_arc: str = "neutral"              # calm→engaged, stable, variable
    
    # Call metadata (for qualification)
    call_duration_sec: float = 0.0
    total_caller_words: int = 0
    total_caller_turns: int = 0
    
    # Timestamp (for logging only — no PII)
    extracted_at: float = 0.0
    
    def qualifies_for_update(self) -> bool:
        """Check if this sample has enough data to update the global signature."""
        return (
            self.call_duration_sec >= MIN_CALL_DURATION_FOR_UPDATE and
            self.total_caller_words >= 30 and      # Minimum 30 words
            self.total_caller_turns >= 3             # Minimum 3 turns
        )


@dataclass
class GlobalSignature:
    """Alan's persistent acoustic identity — the learned self.
    
    This evolves slowly across many calls. No single call can 
    substantially change it. It's a weighted average of every 
    qualifying interaction Alan has ever had.
    """
    
    # Version tracking
    version: str = "1.0"
    last_updated: float = 0.0
    total_calls_absorbed: int = 0
    
    # ---- Learned Parameters ----
    
    # Target speech rate (syllables/sec) — influences TTS speed bias
    speech_rate_target: float = 3.5
    
    # Pause profile — preferred pause durations (in frames; 1 frame = 20ms)
    pause_profile: Dict[str, float] = field(default_factory=lambda: {
        "short": 5.0,      # ~100ms — quick transitions
        "medium": 8.0,     # ~160ms — standard gaps
        "long": 12.0,      # ~240ms — emotional weight
        "extended": 16.0   # ~320ms — deep empathy/reflection
    })
    
    # Breath-to-speech ratio — how often Alan pauses to "breathe"
    breath_ratio_target: float = 0.15
    
    # Filler frequency target (per minute) — not implemented as audio, but
    # influences the text-level filler generation in the LLM prompt
    filler_frequency_target: float = 1.5
    
    # Turn latency target (seconds) — how long Alan waits before speaking
    turn_latency_target: float = 0.40
    
    # Intonation bias (-1 to +1) — tendency toward rising or falling
    intonation_bias: float = 0.0
    
    # ---- Baseline Seeds (NEVER change these — they define Alan's origin) ----
    
    speech_rate_baseline: float = 3.5
    breath_ratio_baseline: float = 0.15
    filler_freq_baseline: float = 1.5
    turn_latency_baseline: float = 0.40
    
    # ---- Lineage Log (last N updates for auditing) ----
    lineage: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'GlobalSignature':
        obj = cls()
        for k, v in d.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        return obj


@dataclass
class EffectiveSignature:
    """The blended signature for THIS call = global + caller influence.
    
    This is what Organs 7-10 actually see as bias parameters.
    Computed once after enough caller speech is heard, then periodically
    updated as more caller data comes in.
    """
    
    # Speed bias (applied as multiplier to PROSODY_SPEED values)
    speed_bias: float = 1.0           # 1.0 = no change, 0.95 = 5% slower
    
    # Silence bias (applied as additive frames to PROSODY_SILENCE_FRAMES)
    silence_bias_frames: int = 0      # +2 = 40ms more silence, -1 = 20ms less
    
    # Breath probability bias (added to breath injection probability)
    breath_prob_bias: float = 0.0     # +0.05 = 5% more likely to breathe
    
    # Turn latency target for this call
    turn_latency_target: float = 0.40
    
    # Source tracking
    caller_influence_pct: float = 0.0  # How much caller influenced this (0-1)


# =============================================================================
# EXTRACTION ENGINE — Per-Call Pattern Analysis
# =============================================================================

class SignatureExtractor:
    """Extracts caller acoustic patterns from STT output and call metadata.
    
    This runs DURING the call, accumulating data from each caller turn.
    At call end, it produces a SignatureSample.
    
    SAFETY: No audio is stored. No voiceprints. No caller identity.
    Only anonymized timing/rhythm metrics from STT text + timestamps.
    """
    
    def __init__(self):
        self._call_start: float = 0.0
        self._caller_turns: List[Dict] = []
        self._total_filler_count: int = 0
        self._total_caller_words: int = 0
        self._total_caller_duration_est: float = 0.0
        self._total_pause_time_est: float = 0.0
        self._turn_latencies: List[float] = []
        self._rising_count: int = 0
        self._falling_count: int = 0
        self._sentiment_trajectory: List[str] = []
        self._alan_last_spoke_at: float = 0.0
    
    def start_call(self):
        """Initialize extraction for a new call."""
        self._call_start = time.time()
        self._caller_turns = []
        self._total_filler_count = 0
        self._total_caller_words = 0
        self._total_caller_duration_est = 0.0
        self._total_pause_time_est = 0.0
        self._turn_latencies = []
        self._rising_count = 0
        self._falling_count = 0
        self._sentiment_trajectory = []
        self._alan_last_spoke_at = time.time()
    
    def record_alan_finished_speaking(self):
        """Mark when Alan finishes a turn (for turn latency measurement)."""
        self._alan_last_spoke_at = time.time()
    
    def process_caller_turn(self, text: str, sentiment: str = "neutral"):
        """Process a single caller turn for signature extraction.
        
        Args:
            text: The STT-transcribed caller text
            sentiment: Detected sentiment for this turn
        """
        now = time.time()
        
        # --- Word count ---
        words = text.split()
        word_count = len(words)
        self._total_caller_words += word_count
        
        # --- Filler detection ---
        text_lower = text.lower()
        for filler in FILLER_WORDS:
            # Count each occurrence
            if ' ' in filler:
                # Multi-word filler
                self._total_filler_count += text_lower.count(filler)
            else:
                # Single-word filler — match whole word boundaries
                self._total_filler_count += len(
                    re.findall(r'\b' + re.escape(filler) + r'\b', text_lower)
                )
        
        # --- Speech rate estimation ---
        # Rough: ~1.5 syllables per word average in English
        est_syllables = word_count * 1.5
        # Estimate speech duration from word count (avg ~3.5 syl/sec)
        # This is ROUGH — we refine with actual timing if available
        est_duration = max(est_syllables / 3.5, 0.5)  # At least 500ms
        self._total_caller_duration_est += est_duration
        
        # --- Pause estimation (inter-sentence) ---
        # Count sentence-ending punctuation as pause indicators
        sentences = re.split(r'[.!?]+', text)
        sentence_count = max(len([s for s in sentences if s.strip()]), 1)
        if sentence_count > 1:
            # Rough pause estimate: ~200ms between sentences
            pause_time = (sentence_count - 1) * 0.2
            self._total_pause_time_est += pause_time
        
        # --- Turn latency ---
        if self._alan_last_spoke_at > 0:
            latency = now - self._alan_last_spoke_at
            # Only count reasonable latencies (0.1s - 5.0s)
            if 0.1 <= latency <= 5.0:
                self._turn_latencies.append(latency)
        
        # --- Intonation tendency ---
        trimmed = text.strip()
        if trimmed.endswith('?'):
            self._rising_count += 1
        elif trimmed.endswith('.') or trimmed.endswith('!'):
            self._falling_count += 1
        
        # --- Sentiment trajectory ---
        self._sentiment_trajectory.append(sentiment)
        
        # --- Store turn metadata ---
        self._caller_turns.append({
            'word_count': word_count,
            'timestamp': now,
            'sentiment': sentiment
        })
    
    def finalize(self) -> SignatureSample:
        """Produce the final SignatureSample for this call.
        
        Called at call end. Returns anonymized pattern metrics only.
        """
        call_duration = time.time() - self._call_start if self._call_start > 0 else 0.0
        
        # --- Average speech rate ---
        if self._total_caller_duration_est > 0:
            total_syllables = self._total_caller_words * 1.5
            avg_rate = total_syllables / self._total_caller_duration_est
        else:
            avg_rate = 3.5  # Default
        
        # --- Pause distribution (rough) ---
        # Since we don't have precise word-level timestamps from STT,
        # we estimate from sentence structure
        short_pauses = 0
        medium_pauses = 0  
        long_pauses = 0
        extended_pauses = 0
        
        for i in range(1, len(self._caller_turns)):
            gap = self._caller_turns[i]['timestamp'] - self._caller_turns[i-1]['timestamp']
            # Subtract estimated speech time of previous turn
            prev_duration = self._caller_turns[i-1]['word_count'] * 1.5 / 3.5
            pause_est = gap - prev_duration
            if 0.12 <= pause_est < 0.20:
                short_pauses += 1
            elif 0.20 <= pause_est < 0.35:
                medium_pauses += 1
            elif 0.35 <= pause_est < 0.60:
                long_pauses += 1
            elif pause_est >= 0.60:
                extended_pauses += 1
        
        # --- Breath-to-speech ratio ---
        total_time = self._total_caller_duration_est + self._total_pause_time_est
        if total_time > 0:
            breath_ratio = self._total_pause_time_est / total_time
        else:
            breath_ratio = 0.15
        
        # --- Filler frequency (per minute) ---
        caller_minutes = self._total_caller_duration_est / 60.0
        if caller_minutes > 0.1:
            filler_freq = self._total_filler_count / caller_minutes
        else:
            filler_freq = 2.0
        
        # --- Turn latency average ---
        if self._turn_latencies:
            avg_latency = sum(self._turn_latencies) / len(self._turn_latencies)
        else:
            avg_latency = 0.45
        
        # --- Intonation tendency ---
        total_intonation = self._rising_count + self._falling_count
        if total_intonation > 0:
            intonation = (self._rising_count - self._falling_count) / total_intonation
        else:
            intonation = 0.0
        
        # --- Emotional arc ---
        if len(self._sentiment_trajectory) >= 3:
            first_third = self._sentiment_trajectory[:len(self._sentiment_trajectory)//3]
            last_third = self._sentiment_trajectory[-(len(self._sentiment_trajectory)//3):]
            
            neg_early = sum(1 for s in first_third if s == 'negative')
            pos_late = sum(1 for s in last_third if s == 'positive')
            neg_late = sum(1 for s in last_third if s == 'negative')
            
            if neg_early > 0 and pos_late > neg_late:
                arc = "anxious_to_relieved"
            elif pos_late > len(last_third) * 0.5:
                arc = "calm_to_engaged"
            elif neg_late > len(last_third) * 0.5:
                arc = "declining"
            else:
                arc = "stable"
        else:
            arc = "neutral"
        
        return SignatureSample(
            avg_speech_rate=round(avg_rate, 2),
            pauses_120_200ms=short_pauses,
            pauses_200_350ms=medium_pauses,
            pauses_350_600ms=long_pauses,
            pauses_600ms_plus=extended_pauses,
            breath_to_speech_ratio=round(breath_ratio, 3),
            filler_frequency=round(filler_freq, 2),
            avg_turn_latency=round(avg_latency, 3),
            intonation_tendency=round(intonation, 2),
            emotional_arc=arc,
            call_duration_sec=round(call_duration, 1),
            total_caller_words=self._total_caller_words,
            total_caller_turns=len(self._caller_turns),
            extracted_at=time.time()
        )


# =============================================================================
# PATTERN LEARNING ENGINE — Slow, Stable Identity Evolution
# =============================================================================

class SignatureLearner:
    """Manages Alan's global signature — the persistent learned identity.
    
    Thread-safe. Loads from disk on init. Saves after each qualifying update.
    Uses exponential moving averages with drift limits.
    """
    
    def __init__(self, state_dir: str = "."):
        self._state_dir = state_dir
        self._state_file = os.path.join(state_dir, SIGNATURE_STATE_FILE)
        self._lock = threading.Lock()
        self._global_sig = self._load_state()
        logger.info(f"[ORGAN 11] Signature Learner initialized — "
                    f"v{self._global_sig.version}, "
                    f"{self._global_sig.total_calls_absorbed} calls absorbed, "
                    f"speech_rate={self._global_sig.speech_rate_target:.2f}")
    
    def _load_state(self) -> GlobalSignature:
        """Load global signature from disk, or create default seed."""
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file, 'r') as f:
                    data = json.load(f)
                sig = GlobalSignature.from_dict(data)
                logger.info(f"[ORGAN 11] Loaded signature state: v{sig.version} ({sig.total_calls_absorbed} calls)")
                return sig
        except Exception as e:
            logger.warning(f"[ORGAN 11] Failed to load signature state: {e} — using seed defaults")
        return GlobalSignature()
    
    def _save_state(self):
        """Persist global signature to disk."""
        try:
            with open(self._state_file, 'w') as f:
                json.dump(self._global_sig.to_dict(), f, indent=2)
            logger.info(f"[ORGAN 11] Signature state saved: v{self._global_sig.version}")
        except Exception as e:
            logger.warning(f"[ORGAN 11] Failed to save signature state: {e}")
    
    def get_global_signature(self) -> GlobalSignature:
        """Get a copy of the current global signature (thread-safe read)."""
        with self._lock:
            return GlobalSignature.from_dict(self._global_sig.to_dict())
    
    def _clamp_drift(self, current: float, baseline: float, max_drift: float) -> float:
        """Ensure a parameter hasn't drifted beyond constitutional limits."""
        low = baseline * (1.0 - max_drift)
        high = baseline * (1.0 + max_drift)
        return max(low, min(high, current))
    
    def absorb_sample(self, sample: SignatureSample) -> bool:
        """Absorb a qualifying SignatureSample into the global signature.
        
        Returns True if the sample was absorbed, False if rejected.
        """
        if not sample.qualifies_for_update():
            logger.info(f"[ORGAN 11] Sample rejected — below thresholds "
                       f"(dur={sample.call_duration_sec:.0f}s, "
                       f"words={sample.total_caller_words}, "
                       f"turns={sample.total_caller_turns})")
            return False
        
        with self._lock:
            sig = self._global_sig
            w = GLOBAL_EMA_WEIGHT  # 0.02
            
            # Store pre-update values for lineage
            pre = {
                'speech_rate': sig.speech_rate_target,
                'breath_ratio': sig.breath_ratio_target,
                'filler_freq': sig.filler_frequency_target,
                'turn_latency': sig.turn_latency_target,
                'intonation': sig.intonation_bias
            }
            
            # --- EMA Update: Speech Rate ---
            sig.speech_rate_target = (1 - w) * sig.speech_rate_target + w * sample.avg_speech_rate
            sig.speech_rate_target = self._clamp_drift(
                sig.speech_rate_target, sig.speech_rate_baseline, MAX_SPEECH_RATE_DRIFT
            )
            
            # --- EMA Update: Breath Ratio ---
            sig.breath_ratio_target = (1 - w) * sig.breath_ratio_target + w * sample.breath_to_speech_ratio
            sig.breath_ratio_target = self._clamp_drift(
                sig.breath_ratio_target, sig.breath_ratio_baseline, MAX_BREATH_RATIO_DRIFT
            )
            
            # --- EMA Update: Filler Frequency ---
            sig.filler_frequency_target = (1 - w) * sig.filler_frequency_target + w * sample.filler_frequency
            sig.filler_frequency_target = self._clamp_drift(
                sig.filler_frequency_target, sig.filler_freq_baseline, MAX_FILLER_DRIFT
            )
            
            # --- EMA Update: Turn Latency ---
            sig.turn_latency_target = (1 - w) * sig.turn_latency_target + w * sample.avg_turn_latency
            sig.turn_latency_target = self._clamp_drift(
                sig.turn_latency_target, sig.turn_latency_baseline, MAX_TURN_LATENCY_DRIFT
            )
            
            # --- EMA Update: Intonation Bias ---
            sig.intonation_bias = (1 - w) * sig.intonation_bias + w * sample.intonation_tendency
            sig.intonation_bias = max(-1.0, min(1.0, sig.intonation_bias))
            
            # --- EMA Update: Pause Profile ---
            total_pauses = (sample.pauses_120_200ms + sample.pauses_200_350ms + 
                           sample.pauses_350_600ms + sample.pauses_600ms_plus)
            if total_pauses > 0:
                # Compute caller's pause profile as weighted average duration
                caller_short_ratio = sample.pauses_120_200ms / total_pauses
                caller_medium_ratio = sample.pauses_200_350ms / total_pauses
                caller_long_ratio = sample.pauses_350_600ms / total_pauses
                
                # Shift pause profile toward caller's distribution
                if caller_short_ratio > 0.6:  # Fast talker — shorter pauses preferred
                    sig.pause_profile['short'] = (1 - w) * sig.pause_profile['short'] + w * 4.0
                    sig.pause_profile['medium'] = (1 - w) * sig.pause_profile['medium'] + w * 6.0
                elif caller_long_ratio > 0.3:  # Deliberate talker — longer pauses
                    sig.pause_profile['medium'] = (1 - w) * sig.pause_profile['medium'] + w * 10.0
                    sig.pause_profile['long'] = (1 - w) * sig.pause_profile['long'] + w * 14.0
                
                # Clamp pause profile
                sig.pause_profile['short'] = max(3.0, min(8.0, sig.pause_profile['short']))
                sig.pause_profile['medium'] = max(5.0, min(12.0, sig.pause_profile['medium']))
                sig.pause_profile['long'] = max(8.0, min(18.0, sig.pause_profile['long']))
                sig.pause_profile['extended'] = max(12.0, min(22.0, sig.pause_profile['extended']))
            
            # --- Bookkeeping ---
            sig.total_calls_absorbed += 1
            sig.last_updated = time.time()
            
            # --- Lineage entry (keep last 50) ---
            post = {
                'speech_rate': round(sig.speech_rate_target, 3),
                'breath_ratio': round(sig.breath_ratio_target, 4),
                'filler_freq': round(sig.filler_frequency_target, 2),
                'turn_latency': round(sig.turn_latency_target, 3),
                'intonation': round(sig.intonation_bias, 3)
            }
            
            lineage_entry = {
                'call_number': sig.total_calls_absorbed,
                'timestamp': time.time(),
                'pre': pre,
                'post': post,
                'sample_summary': {
                    'duration': sample.call_duration_sec,
                    'words': sample.total_caller_words,
                    'turns': sample.total_caller_turns,
                    'arc': sample.emotional_arc
                }
            }
            sig.lineage.append(lineage_entry)
            if len(sig.lineage) > 50:
                sig.lineage = sig.lineage[-50:]
            
            # Bump version
            major, minor = sig.version.split('.')
            sig.version = f"{major}.{int(minor) + 1}"
            
            # Persist
            self._save_state()
            
            logger.info(f"[ORGAN 11] Signature absorbed call #{sig.total_calls_absorbed} → v{sig.version} | "
                       f"speech_rate: {pre['speech_rate']:.2f}→{post['speech_rate']:.2f}, "
                       f"breath: {pre['breath_ratio']:.3f}→{post['breath_ratio']:.3f}, "
                       f"latency: {pre['turn_latency']:.3f}→{post['turn_latency']:.3f}")
            
            return True
    
    def reset_to_baseline(self, reason: str = "manual reset"):
        """Reset global signature to baseline seed values (constitutional reset)."""
        with self._lock:
            old_version = self._global_sig.version
            old_calls = self._global_sig.total_calls_absorbed
            
            self._global_sig = GlobalSignature()
            self._global_sig.lineage = [{
                'call_number': 0,
                'timestamp': time.time(),
                'pre': {'reason': f'RESET from v{old_version} ({old_calls} calls): {reason}'},
                'post': {'speech_rate': 3.5, 'breath_ratio': 0.15, 'filler_freq': 1.5, 'turn_latency': 0.40}
            }]
            
            self._save_state()
            logger.warning(f"[ORGAN 11] SIGNATURE RESET — v{old_version} ({old_calls} calls) → v1.0 (reason: {reason})")


# =============================================================================
# BIAS COMPUTER — Translates Signature → Prosody Parameters
# =============================================================================

def compute_effective_signature(
    global_sig: GlobalSignature,
    caller_sample: Optional[SignatureSample] = None
) -> EffectiveSignature:
    """Compute the effective signature for this call.
    
    Blends global learned identity (70%) with current caller patterns (30%).
    Outputs bias parameters that Organs 7-10 can consume without knowing
    about Organ 11.
    
    Args:
        global_sig: Alan's persistent learned signature
        caller_sample: Pattern sample from current call (may be partial)
    
    Returns:
        EffectiveSignature with bias values for prosody engine
    """
    eff = EffectiveSignature()
    
    if caller_sample is None or caller_sample.total_caller_words < 10:
        # Not enough caller data yet — use pure global signature
        # Convert global signature parameters to bias values
        baseline_rate = 3.5
        rate_ratio = global_sig.speech_rate_target / baseline_rate
        
        # If caller speaks fast, Alan speeds up slightly (and vice versa)
        # Map speech rate ratio to speed bias: 1.0 means no change
        eff.speed_bias = 0.5 + 0.5 * rate_ratio  # Maps [0.5x, 1.5x] → [0.75, 1.25]
        eff.speed_bias = max(0.90, min(1.10, eff.speed_bias))  # Cap at ±10%
        
        # Pause bias: global pause profile vs baseline
        baseline_medium = 8.0
        pause_ratio = global_sig.pause_profile.get('medium', 8.0) / baseline_medium
        eff.silence_bias_frames = round((pause_ratio - 1.0) * 4)  # ±4 frames max
        eff.silence_bias_frames = max(-3, min(3, eff.silence_bias_frames))
        
        # Breath bias from global breath ratio
        baseline_breath = 0.15
        breath_diff = global_sig.breath_ratio_target - baseline_breath
        eff.breath_prob_bias = breath_diff * 2.0  # Scale up for effect
        eff.breath_prob_bias = max(-0.10, min(0.10, eff.breath_prob_bias))
        
        eff.turn_latency_target = global_sig.turn_latency_target
        eff.caller_influence_pct = 0.0
        return eff
    
    # --- Blend global (70%) + caller (30%) ---
    w = LOCAL_BLEND_WEIGHT  # 0.30
    
    # Speech rate blend
    blended_rate = (1 - w) * global_sig.speech_rate_target + w * caller_sample.avg_speech_rate
    baseline_rate = 3.5
    rate_ratio = blended_rate / baseline_rate
    eff.speed_bias = 0.5 + 0.5 * rate_ratio
    eff.speed_bias = max(0.90, min(1.10, eff.speed_bias))
    
    # Pause profile blend — infer caller's preferred pause from their data
    total_caller_pauses = (caller_sample.pauses_120_200ms + caller_sample.pauses_200_350ms +
                          caller_sample.pauses_350_600ms + caller_sample.pauses_600ms_plus)
    if total_caller_pauses > 0:
        # Weighted average caller pause preference (in frames)
        caller_pause_pref = (
            caller_sample.pauses_120_200ms * 5.0 +    # ~100ms = 5 frames
            caller_sample.pauses_200_350ms * 8.0 +     # ~160ms = 8 frames
            caller_sample.pauses_350_600ms * 12.0 +    # ~240ms = 12 frames
            caller_sample.pauses_600ms_plus * 18.0     # ~360ms = 18 frames
        ) / total_caller_pauses
    else:
        caller_pause_pref = 8.0
    
    blended_pause = (1 - w) * global_sig.pause_profile.get('medium', 8.0) + w * caller_pause_pref
    baseline_pause = 8.0
    eff.silence_bias_frames = round((blended_pause / baseline_pause - 1.0) * 4)
    eff.silence_bias_frames = max(-3, min(3, eff.silence_bias_frames))
    
    # Breath ratio blend
    blended_breath = (1 - w) * global_sig.breath_ratio_target + w * caller_sample.breath_to_speech_ratio
    baseline_breath = 0.15
    breath_diff = blended_breath - baseline_breath
    eff.breath_prob_bias = breath_diff * 2.0
    eff.breath_prob_bias = max(-0.10, min(0.10, eff.breath_prob_bias))
    
    # Turn latency blend
    eff.turn_latency_target = (1 - w) * global_sig.turn_latency_target + w * caller_sample.avg_turn_latency
    
    eff.caller_influence_pct = w
    
    return eff


# =============================================================================
# INTEGRATION HELPERS — Connect to Relay Server Pipeline
# =============================================================================

# Module-level singleton (initialized on first import from relay server)
_SIGNATURE_LEARNER: Optional[SignatureLearner] = None
_SIGNATURE_LEARNER_LOCK = threading.Lock()


def get_signature_learner(state_dir: str = ".") -> SignatureLearner:
    """Get or create the global SignatureLearner singleton."""
    global _SIGNATURE_LEARNER
    if _SIGNATURE_LEARNER is None:
        with _SIGNATURE_LEARNER_LOCK:
            if _SIGNATURE_LEARNER is None:
                _SIGNATURE_LEARNER = SignatureLearner(state_dir=state_dir)
    return _SIGNATURE_LEARNER


def get_prosody_speed_bias(effective_sig: EffectiveSignature, base_speed: float) -> float:
    """Apply signature speed bias to a prosody speed value.
    
    Args:
        effective_sig: Current effective signature for this call
        base_speed: The base speed from PROSODY_SPEED[intent]
    
    Returns:
        Adjusted speed value (e.g., 1.12 → 1.14 if caller is slightly fast)
    """
    return round(base_speed * effective_sig.speed_bias, 2)


def get_prosody_silence_bias(effective_sig: EffectiveSignature, base_frames: int) -> int:
    """Apply signature silence bias to a prosody silence frame count.
    
    Args:
        effective_sig: Current effective signature for this call
        base_frames: The base frames from PROSODY_SILENCE_FRAMES[intent]
    
    Returns:
        Adjusted frame count (never below 2, never above 20)
    """
    adjusted = base_frames + effective_sig.silence_bias_frames
    return max(2, min(20, adjusted))


def get_breath_probability_bias(effective_sig: EffectiveSignature, base_prob: float) -> float:
    """Apply signature breath probability bias.
    
    Args:
        effective_sig: Current effective signature for this call
        base_prob: Base breath probability (0.0-1.0)
    
    Returns:
        Adjusted probability (clamped 0.0-1.0)
    """
    adjusted = base_prob + effective_sig.breath_prob_bias
    return max(0.0, min(1.0, adjusted))


# =============================================================================
# BOOT LOG
# =============================================================================

logging.info("[ORGAN 11] Signature Extraction & Adaptive Voice Identity — LOADED")
logging.info("[ORGAN 11] Safety: No raw audio | No voiceprints | No identity mimicry | Patterns only")
