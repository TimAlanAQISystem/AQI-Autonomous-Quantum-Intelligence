"""
+==============================================================================+
|   EAB-PLUS BEHAVIOR ROUTER                                                    |
|   AQI Agent Alan --- Environment-Fluent Behavior Routing                      |
|                                                                               |
|   PURPOSE:                                                                    |
|   Route behavior based on EAB-Plus composite resolution signals.              |
|   Maps (env_class, hangup_risk, prosody) → (action, template, governance).    |
|                                                                               |
|   ARCHITECTURE:                                                               |
|     1. select_action() — env_class → EnvironmentAction                        |
|     2. select_template() — action → behavior template function                |
|     3. adapt_behavior() — hangup_risk + prosody → behavioral modifiers        |
|     4. route() — composite: select + adapt + apply                            |
|                                                                               |
|   INTEGRATION:                                                                |
|     Called after eab_plus.resolve() in the STT pipeline.                      |
|     Result feeds into LLM prompt or direct TTS (for non-human envs).          |
|                                                                               |
|   LINEAGE: Built 2026-02-20. Tim's EAB-Plus architecture spec.               |
+==============================================================================+
"""

import logging
from typing import Dict, Any, Optional, Callable

from call_environment_classifier import (
    EnvironmentClass,
    EnvironmentAction,
    EnvironmentBehaviorTemplates,
)

logger = logging.getLogger("EAB_PLUS_ROUTER")


# ======================================================================
#  EXTENDED BEHAVIOR TEMPLATES
#  Augment existing templates with EAB-Plus awareness.
# ======================================================================

class EABPlusBehaviorTemplates:
    """
    Enhanced behavior templates that are aware of EAB-Plus signals.

    Extends the base EnvironmentBehaviorTemplates with:
    - Hangup-risk-adapted variants (shorter/more direct)
    - Prosody-adapted variants (tone matching)
    - Lead-history-adapted variants (warm follow-up)
    """

    # --- Core templates (delegate to base when no adaptation needed) ---

    @staticmethod
    def human_opener(ctx: Dict[str, Any]) -> str:
        """
        Human opener. Returns empty — let normal cognition pipeline handle.
        The EAB system confirms this is a human and the existing
        smart_greeting_routine / pipeline continues as designed.
        """
        return ""

    @staticmethod
    def screen_pass_through(ctx: Dict[str, Any]) -> str:
        """Google Call Screen / carrier screener — attempt pass-through."""
        merchant_name = ctx.get("merchant_name", "")
        cycle = ctx.get("env_cycles", 0)

        if cycle == 0:
            if merchant_name:
                return (f"Hi, this is Alan calling for {merchant_name}. "
                        "It's about their merchant account. Please connect me.")
            return ("Hi, this is Alan calling about a merchant account. "
                    "Please connect me.")
        else:
            return "Alan, merchant services. Please connect me."

    @staticmethod
    def spam_pass_through(ctx: Dict[str, Any]) -> str:
        """Carrier spam blocker — brief identification."""
        return "Alan, merchant services. Connect."

    @staticmethod
    def ivr_navigation(ctx: Dict[str, Any]) -> str:
        """Business IVR — attempt to reach a human."""
        return "Hi, I'm calling for the business owner."

    @staticmethod
    def voicemail_drop(ctx: Dict[str, Any]) -> str:
        """Voicemail — drop short message and abort."""
        recommendation = ctx.get("lead_recommendation", "")
        if recommendation == "expect_voicemail":
            # Lead historically goes to VM — ultra-short
            return "Hey, it's Alan again — trying you back. I'll follow up soon."
        return "Hey, this is Alan — I'll try you again later."

    @staticmethod
    def answering_service_decline(ctx: Dict[str, Any]) -> str:
        """Answering service — decline to leave message."""
        merchant_name = ctx.get("merchant_name", "")
        if merchant_name:
            return f"Alan calling for {merchant_name}. I'll try them back directly."
        return "No worries, I'll try back directly."

    @staticmethod
    def ai_receptionist_pass_through(ctx: Dict[str, Any]) -> str:
        """AI receptionist — clearly state purpose for automated routing."""
        merchant_name = ctx.get("merchant_name", "")
        if merchant_name:
            return (f"Alan calling for {merchant_name} about their "
                    "merchant account. Please connect me.")
        return ("Alan calling about a merchant account. "
                "Please connect me.")

    @staticmethod
    def live_receptionist_opener(ctx: Dict[str, Any]) -> str:
        """Live receptionist — warm handoff request."""
        merchant_name = ctx.get("merchant_name", "")
        if merchant_name:
            return (f"Hi there — Alan calling for {merchant_name} "
                    "about their merchant account.")
        return "Hi there — Alan calling about a merchant account."

    @staticmethod
    def fallback_opener(ctx: Dict[str, Any]) -> str:
        """Unknown environment — safe neutral opener. Let pipeline handle."""
        return ""

    @staticmethod
    def warm_followup_opener(ctx: Dict[str, Any]) -> str:
        """Lead history indicates warm follow-up. Previous human contact."""
        merchant_name = ctx.get("merchant_name", "")
        if merchant_name:
            return (f"Hey {merchant_name}, it's Alan calling back "
                    "from Signature Card Services.")
        return "Hey, it's Alan calling back from Signature Card Services."

    @staticmethod
    def high_risk_salvage(ctx: Dict[str, Any]) -> str:
        """
        Hangup risk > 0.7 — shorten everything, go to value.
        This injects a directive into the LLM prompt, not direct TTS.
        """
        return ""  # Handled via prompt modifier, not direct TTS


# ======================================================================
#  BEHAVIOR ROUTER
# ======================================================================

class EABPlusBehaviorRouter:
    """
    Routes EAB-Plus signals to behavioral decisions.

    Architecture:
        eab_result = eab_plus.resolve(...)
        route_result = behavior_router.route(call_ctx, eab_result)
        if route_result["tts_text"]:
            tts.say(call_ctx, route_result["tts_text"])
        else:
            # Normal cognition pipeline handles it
            apply_modifiers(route_result["modifiers"])
    """

    def __init__(self):
        self.templates = EABPlusBehaviorTemplates()
        self._action_map = self._build_action_map()
        self._template_map = self._build_template_map()

    def _build_action_map(self) -> Dict[str, EnvironmentAction]:
        """Map environment class names to default actions."""
        return {
            "GOOGLE_CALL_SCREEN": EnvironmentAction.PASS_THROUGH,
            "CARRIER_SPAM_BLOCKER": EnvironmentAction.PASS_THROUGH,
            "BUSINESS_IVR": EnvironmentAction.NAVIGATE,
            "PERSONAL_VOICEMAIL": EnvironmentAction.DROP_AND_ABORT,
            "CARRIER_VOICEMAIL": EnvironmentAction.DROP_AND_ABORT,
            "AI_RECEPTIONIST": EnvironmentAction.PASS_THROUGH,
            "LIVE_RECEPTIONIST": EnvironmentAction.PASS_THROUGH,
            "ANSWERING_SERVICE": EnvironmentAction.DECLINE_AND_ABORT,
            "HUMAN": EnvironmentAction.CONTINUE_MISSION,
            "UNKNOWN": EnvironmentAction.FALLBACK,
        }

    def _build_template_map(self) -> Dict[str, Callable]:
        """Map (env_class, action) → template function."""
        return {
            "GOOGLE_CALL_SCREEN": self.templates.screen_pass_through,
            "CARRIER_SPAM_BLOCKER": self.templates.spam_pass_through,
            "BUSINESS_IVR": self.templates.ivr_navigation,
            "PERSONAL_VOICEMAIL": self.templates.voicemail_drop,
            "CARRIER_VOICEMAIL": self.templates.voicemail_drop,
            "AI_RECEPTIONIST": self.templates.ai_receptionist_pass_through,
            "LIVE_RECEPTIONIST": self.templates.live_receptionist_opener,
            "ANSWERING_SERVICE": self.templates.answering_service_decline,
            "HUMAN": self.templates.human_opener,
            "UNKNOWN": self.templates.fallback_opener,
        }

    def select_action(self, env_class: str,
                      hangup_risk: float = 0.0) -> EnvironmentAction:
        """
        Select environment action based on class and risk signals.

        Args:
            env_class: Environment classification string.
            hangup_risk: Predicted hang-up risk [0,1].

        Returns:
            EnvironmentAction enum value.
        """
        action = self._action_map.get(env_class, EnvironmentAction.FALLBACK)

        # If in HUMAN mode but hangup_risk is extremely high,
        # don't change the action — but signal it for behavior adaptation
        # (handled in route() via modifiers)

        return action

    def select_template(self, env_class: str, action: EnvironmentAction,
                        lead_recommendation: str = "") -> Callable:
        """
        Select the behavior template function.

        Args:
            env_class: Environment classification string.
            action: Selected EnvironmentAction.
            lead_recommendation: Lead history recommendation string.

        Returns:
            Template function that takes ctx dict and returns TTS text.
        """
        # Special case: warm follow-up from lead history
        if (action == EnvironmentAction.CONTINUE_MISSION and
                lead_recommendation == "warm_followup"):
            return self.templates.warm_followup_opener

        return self._template_map.get(env_class, self.templates.fallback_opener)

    def compute_modifiers(self, eab_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute behavioral modifiers from EAB-Plus signals.

        These modifiers affect the LLM prompt and TTS parameters,
        NOT the template selection.

        Returns:
            {
                "force_brief": bool — shorten response
                "max_tokens": int — token limit override
                "tone_directive": str — LLM prompt injection
                "tts_speed_modifier": float — TTS speed multiplier
                "yield_floor": bool — stop and listen
            }
        """
        mods = {
            "force_brief": False,
            "max_tokens": 80,
            "tone_directive": "",
            "tts_speed_modifier": 1.0,
            "yield_floor": False,
        }

        hangup_risk = eab_result.get("hangup_risk", 0.0)
        prosody = eab_result.get("prosody", {})

        # --- Hangup risk adaptations ---
        if hangup_risk >= 0.7:
            mods["force_brief"] = True
            mods["max_tokens"] = 40
            mods["tone_directive"] = (
                "The merchant seems ready to hang up. Keep your response "
                "VERY short (1-2 sentences max). Lead with your strongest "
                "value point or ask a direct closing question. No explanations."
            )
        elif hangup_risk >= 0.5:
            mods["max_tokens"] = 60
            mods["tone_directive"] = (
                "The merchant seems impatient. Keep it concise. "
                "Get to the point quickly."
            )

        # --- Prosody emotion adaptations ---
        if prosody.get("emotion_busy", 0) > 0.5:
            mods["tts_speed_modifier"] = 1.08
            if not mods["tone_directive"]:
                mods["tone_directive"] = (
                    "The merchant sounds busy. Speak efficiently. "
                    "Respect their time."
                )

        if prosody.get("emotion_annoyed", 0) > 0.4:
            if not mods["tone_directive"]:
                mods["tone_directive"] = (
                    "The merchant sounds annoyed. Soften your tone. "
                    "Be respectful and brief. Don't push."
                )

        if prosody.get("emotion_curious", 0) > 0.5:
            # Curious = good sign, let Alan elaborate slightly
            mods["max_tokens"] = min(mods["max_tokens"] + 20, 100)

        return mods

    def route(self, call_ctx: Dict[str, Any],
              eab_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Master routing: combine env classification + signals into behavioral
        decision.

        Args:
            call_ctx: Call context dict with merchant_name, env_cycles, etc.
            eab_result: Output from EABPlusResolver.resolve().

        Returns:
            {
                "tts_text": str — direct TTS text (empty = use cognition pipeline)
                "env_class": str
                "env_action": str
                "env_behavior": str — template function name
                "hangup_risk": float
                "modifiers": dict — behavioral modifiers for LLM/TTS
                "should_abort": bool — if True, end the call
            }
        """
        env_class = eab_result.get("env_class", "UNKNOWN")
        hangup_risk = eab_result.get("hangup_risk", 0.0)
        lead_prior = eab_result.get("lead_prior", {})
        lead_recommendation = lead_prior.get("recommendation", "")

        # 1. Select action
        action = self.select_action(env_class, hangup_risk)

        # 2. Select template
        template_fn = self.select_template(env_class, action, lead_recommendation)

        # 3. Compute behavioral modifiers
        modifiers = self.compute_modifiers(eab_result)

        # 4. Inject lead recommendation into context for template use
        call_ctx["lead_recommendation"] = lead_recommendation

        # 5. Generate TTS text from template
        tts_text = template_fn(call_ctx)

        # 6. Update call context
        call_ctx["env_class"] = env_class
        call_ctx["env_action"] = action.name
        call_ctx["env_behavior"] = template_fn.__name__
        call_ctx["hangup_risk"] = hangup_risk

        # 7. Determine if call should abort
        should_abort = action in (
            EnvironmentAction.DROP_AND_ABORT,
            EnvironmentAction.DECLINE_AND_ABORT,
        )

        result = {
            "tts_text": tts_text,
            "env_class": env_class,
            "env_action": action.name,
            "env_behavior": template_fn.__name__,
            "hangup_risk": hangup_risk,
            "modifiers": modifiers,
            "should_abort": should_abort,
        }

        logger.info(
            f"[EAB-PLUS ROUTER] env={env_class} action={action.name} "
            f"behavior={template_fn.__name__} hangup_risk={hangup_risk:.2f} "
            f"abort={should_abort} brief={modifiers['force_brief']}"
        )

        return result
