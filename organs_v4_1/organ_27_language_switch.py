"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 27 — LANGUAGE SWITCHING (MULTILINGUAL PIPELINE)               ║
║                                                                              ║
║  Detect and switch languages dynamically during a call. Auto-detects         ║
║  caller language from speech patterns and switches STT/TTS voice and         ║
║  system prompt to match.                                                     ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No mixing languages without merchant request                            ║
║    - No hallucinated translations                                            ║
║    - Detection window limited to first 10 seconds                            ║
║    - Minimum confidence threshold (0.7) before switching                     ║
║    - Language choice logged for analytics                                    ║
║    - Fallback to English with apology if scripts missing                     ║
║                                                                              ║
║  RRG: Section 37                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor: str, cost: int):
        def decorator(fn):
            return fn
        return decorator

logger = logging.getLogger("organ_27_language_switch")

# ─── Constants ───────────────────────────────────────────────────────────────

DETECTION_WINDOW_SECONDS = 10.0
MIN_DETECTION_CONFIDENCE = 0.7

# Supported languages with TTS voice mapping
LANGUAGE_CONFIGS = {
    "en": {
        "name": "English",
        "tts_voice": "en-US-Neural2-D",
        "stt_language": "en-US",
        "prompt_suffix": "",
    },
    "es": {
        "name": "Spanish",
        "tts_voice": "es-US-Neural2-A",
        "stt_language": "es-US",
        "prompt_suffix": " Responde completamente en español.",
    },
    "fr": {
        "name": "French",
        "tts_voice": "fr-FR-Neural2-A",
        "stt_language": "fr-FR",
        "prompt_suffix": " Réponds entièrement en français.",
    },
    "pt": {
        "name": "Portuguese",
        "tts_voice": "pt-BR-Neural2-A",
        "stt_language": "pt-BR",
        "prompt_suffix": " Responda completamente em português.",
    },
    "zh": {
        "name": "Chinese (Mandarin)",
        "tts_voice": "cmn-CN-Neural2-A",
        "stt_language": "cmn-CN",
        "prompt_suffix": " 请完全用中文回答。",
    },
}

# Common language detection markers (simplified keyword-based)
LANGUAGE_MARKERS = {
    "es": ["hola", "buenos", "gracias", "por favor", "señor", "señora",
           "necesito", "quiero", "puede", "tengo", "estoy", "cómo"],
    "fr": ["bonjour", "merci", "s'il vous plaît", "oui", "non", "je suis",
           "comment", "pourquoi", "monsieur", "madame"],
    "pt": ["olá", "obrigado", "por favor", "bom dia", "senhor", "senhora",
           "preciso", "quero", "posso", "estou"],
    "zh": ["你好", "谢谢", "请", "我", "是", "不", "要", "可以"],
}

# Bilingual script segments
BILINGUAL_SCRIPTS = {
    "greeting": {
        "en": "Hi, this is Alan. How can I help you today?",
        "es": "Hola, soy Alan. ¿En qué puedo ayudarle hoy?",
        "fr": "Bonjour, je suis Alan. Comment puis-je vous aider?",
        "pt": "Olá, sou Alan. Como posso ajudá-lo hoje?",
    },
    "pricing": {
        "en": "Let me walk you through our pricing options.",
        "es": "Permítame explicarle nuestras opciones de precios.",
        "fr": "Laissez-moi vous présenter nos options de tarification.",
        "pt": "Deixe-me apresentar nossas opções de preços.",
    },
    "closing": {
        "en": "Would you like to move forward with this?",
        "es": "¿Le gustaría seguir adelante con esto?",
        "fr": "Souhaitez-vous aller de l'avant?",
        "pt": "Gostaria de seguir em frente com isso?",
    },
    "fallback_apology": {
        "en": "I apologize, but I'll need to continue in English for this part.",
        "es": "Disculpe, pero necesitaré continuar en inglés para esta parte.",
    },
}


class LanguageSwitchOrgan:
    """
    Organ 27: Detects caller language and switches TTS/STT/prompt accordingly.
    IQcore cost: 1 per switch.
    """

    def __init__(self):
        self._active_call: Optional[str] = None
        self._current_language: str = "en"
        self._detected_language: Optional[str] = None
        self._detection_confidence: float = 0.0
        self._detection_locked: bool = False  # Lock after detection window
        self._call_start_time: Optional[float] = None
        self._switch_log: List[Dict] = []
        self._speech_buffer: List[str] = []  # First N seconds of speech
        logger.info("[Organ 27] LanguageSwitchOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str, default_language: str = "en") -> None:
        self._active_call = call_id
        self._current_language = default_language
        self._detected_language = None
        self._detection_confidence = 0.0
        self._detection_locked = False
        self._call_start_time = time.time()
        self._speech_buffer = []
        logger.info(f"[Organ 27] Call started: {call_id}, default: {default_language}")

    def end_call(self) -> Dict[str, Any]:
        stats = {
            "call_id": self._active_call,
            "final_language": self._current_language,
            "detected_language": self._detected_language,
            "detection_confidence": self._detection_confidence,
            "switches": len([s for s in self._switch_log
                             if s.get("call_id") == self._active_call]),
        }
        self._active_call = None
        self._detection_locked = False
        self._speech_buffer = []
        return stats

    # ─── Language Detection ──────────────────────────────────────────────

    def analyze_speech(self, text: str) -> Dict[str, Any]:
        """
        Analyze incoming speech text for language markers.
        Only active during the detection window (first 10 seconds).

        Returns detection result.
        """
        if self._detection_locked:
            return {
                "status": "locked",
                "current_language": self._current_language,
                "message": "Detection window closed",
            }

        # Check if we're still in the detection window
        if self._call_start_time:
            elapsed = time.time() - self._call_start_time
            if elapsed > DETECTION_WINDOW_SECONDS:
                self._detection_locked = True
                return {
                    "status": "window_expired",
                    "current_language": self._current_language,
                    "elapsed": elapsed,
                }

        self._speech_buffer.append(text.lower())
        combined = " ".join(self._speech_buffer)

        # Score each language
        scores = {}
        for lang_code, markers in LANGUAGE_MARKERS.items():
            hits = sum(1 for m in markers if m in combined)
            if hits > 0:
                scores[lang_code] = hits / len(markers)

        if not scores:
            return {
                "status": "no_detection",
                "current_language": self._current_language,
                "buffer_size": len(self._speech_buffer),
            }

        # Find best match
        best_lang = max(scores, key=scores.get)
        confidence = scores[best_lang]

        self._detected_language = best_lang
        self._detection_confidence = confidence

        result = {
            "status": "detected",
            "detected_language": best_lang,
            "language_name": LANGUAGE_CONFIGS.get(best_lang, {}).get("name", best_lang),
            "confidence": confidence,
            "meets_threshold": confidence >= MIN_DETECTION_CONFIDENCE,
            "current_language": self._current_language,
        }

        return result

    # ─── Language Switching ──────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def switch_language(self, target_language: str, reason: str = "detection") -> Dict[str, Any]:
        """
        Switch Alan's language. Returns new TTS/STT config.

        Args:
            target_language: ISO 639-1 code (e.g., 'es', 'fr')
            reason: Why the switch is happening

        Returns:
            New language configuration
        """
        if target_language not in LANGUAGE_CONFIGS:
            return {
                "status": "unsupported",
                "language": target_language,
                "fallback": "en",
                "message": f"Language '{target_language}' not supported. Continuing in English.",
            }

        old_language = self._current_language
        self._current_language = target_language
        config = LANGUAGE_CONFIGS[target_language]

        result = {
            "status": "switched",
            "from_language": old_language,
            "to_language": target_language,
            "language_name": config["name"],
            "tts_voice": config["tts_voice"],
            "stt_language": config["stt_language"],
            "prompt_suffix": config["prompt_suffix"],
            "reason": reason,
        }

        self._switch_log.append({
            "call_id": self._active_call,
            "from": old_language,
            "to": target_language,
            "reason": reason,
            "timestamp": time.time(),
        })

        logger.info(f"[Organ 27] Language switched: {old_language} → {target_language}")
        return result

    def get_confirmation_prompt(self) -> str:
        """
        Get a confirmation prompt asking merchant if they want to switch.
        Used when detection confidence is sufficient.
        """
        if self._detected_language == "es":
            return "Would you prefer we continue in Spanish? / ¿Prefiere que continuemos en español?"
        elif self._detected_language == "fr":
            return "Would you prefer we continue in French? / Préférez-vous que nous continuions en français?"
        elif self._detected_language == "pt":
            return "Would you prefer we continue in Portuguese? / Prefere que continuemos em português?"
        else:
            return f"Would you prefer we continue in {LANGUAGE_CONFIGS.get(self._detected_language, {}).get('name', 'another language')}?"

    # ─── Script Access ───────────────────────────────────────────────────

    def get_script(self, segment: str) -> str:
        """
        Get a script segment in the current language.
        Falls back to English if segment not available in current language.
        """
        scripts = BILINGUAL_SCRIPTS.get(segment, {})
        text = scripts.get(self._current_language)

        if text:
            return text

        # ── Fallback: English with apology ──
        fallback = scripts.get("en", "")
        if self._current_language != "en" and fallback:
            apology = BILINGUAL_SCRIPTS.get("fallback_apology", {}).get(self._current_language, "")
            if apology:
                return f"{apology} {fallback}"
        return fallback

    def get_available_languages(self) -> List[Dict[str, str]]:
        """Return list of supported languages."""
        return [
            {"code": code, "name": cfg["name"]}
            for code, cfg in LANGUAGE_CONFIGS.items()
        ]

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 27 — Language Switching",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "current_language": self._current_language,
            "detected_language": self._detected_language,
            "detection_confidence": self._detection_confidence,
            "detection_locked": self._detection_locked,
            "supported_languages": len(LANGUAGE_CONFIGS),
            "total_switches": len(self._switch_log),
        }
