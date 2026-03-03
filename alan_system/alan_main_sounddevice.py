# alan_main_sounddevice.py

"""
Alternative main file using sounddevice instead of PyAudio.
Use this if PyAudio installation fails.
"""

from datetime import datetime
from alan_voice_sounddevice import alan_loop, speak
from alan_memory import (
    init_db,
    start_session,
    end_session,
    add_message,
    append_to_log,
    remember_fact,
    get_fact,
    list_facts,
)
from alan_aqi_autonomous import aqi_system
from aqi_natural_alignment import create_default_alignment_engine, NaturalSignal

current_session_id = None
alignment_engine = create_default_alignment_engine()


def on_session_start():
    global current_session_id
    current_session_id = start_session()
    append_to_log(current_session_id, "system", "Session started.")


def on_session_end():
    global current_session_id
    if current_session_id is not None:
        append_to_log(current_session_id, "system", "Session ended.")
        end_session(current_session_id)
        current_session_id = None


def process_user_utterance(text: str) -> str:
    """
    Process user utterances through the complete autonomous AQI system with natural alignment.
    Handles both general queries and business operations.
    """

    lower_raw = text.lower()

    # Create natural signal for alignment assessment
    signal = NaturalSignal(
        payload=text,
        metadata={
            "origin": "voice_input",
            "intent": "user_query",
            "timestamp": datetime.now().isoformat(),
            "session_id": current_session_id
        }
    )

    # Assess alignment once (read-only)
    alignment_state = alignment_engine.assess_alignment(signal)

    # Diagnostic-only command: do NOT change anything
    if "confirm alignment" in lower_raw or "alignment check" in lower_raw:
        report = alignment_engine.diagnostic_report(signal, alignment_state)
        summary = (
            f"Alignment diagnostic — level: {report['level']}, "
            f"compensation: {report['compensation_score']:.3f} ({report['compensation_type']}). "
            f"Notes: {' | '.join(report['notes'])}"
        )
        append_to_log(current_session_id, "system", summary)
        return summary

    # Apply correction if misaligned (normal flow)
    if alignment_state.level != alignment_engine._qualitative_alignment(0.0, 0)[0]:  # Not fully aligned
        correction_result = alignment_engine.correct(signal, alignment_state)
        alignment_engine.integrate_feedback(correction_result)

        # Use corrected signal
        corrected_text = correction_result.corrected_signal.payload
        append_to_log(current_session_id, "system", f"Alignment correction applied: {correction_result.logs}")
    else:
        corrected_text = text

    lower = corrected_text.lower()

    # Business-related queries
    if any(keyword in lower for keyword in ["status", "leads", "performance", "generate", "business", "merchant"]):
        return aqi_system.process_business_query(text)

    # Fallback to simple fact management for non-business queries
    if lower.startswith("remember that"):
        try:
            after = lower.replace("remember that", "", 1).strip()
            if " is " in after:
                key, value = after.split(" is ", 1)
                key = key.strip()
                value = value.strip()
                remember_fact(key, value)
                return f"Okay, I will remember that {key} is {value}."
        except Exception:
            pass

    if lower.startswith("what is"):
        try:
            key = lower.replace("what is", "", 1).strip().rstrip("?")
            fact = get_fact(key)
            if fact:
                return f"{key} is {fact}."
            else:
                return f"I don't have anything stored for {key} yet."
        except Exception:
            pass

    if "list my facts" in lower:
        facts = list_facts()
        if not facts:
            return "You don't have any stored facts yet."
        parts = [f"{k} is {v}" for k, v in facts.items()]
        return "Here is what I have stored: " + "; ".join(parts)

    # Default business-focused response
    return "I'm here to help with your merchant services business. Ask me about leads, status, or performance."


def on_user_utterance(text: str):
    global current_session_id

    if current_session_id is None:
        # Safety, should not happen if callbacks are correct
        return

    # Log user msg
    add_message(current_session_id, "user", text)
    append_to_log(current_session_id, "user", text)

    # Process through simple logic layer
    response = process_user_utterance(text)

    # Log Alan's response
    add_message(current_session_id, "alan", response)
    append_to_log(current_session_id, "alan", response)

    # Speak
    speak(response)


def main():
    # Initialize DB
    init_db()
    # Start loop
    alan_loop(
        on_user_utterance=on_user_utterance,
        on_session_start=on_session_start,
        on_session_end=on_session_end
    )


if __name__ == "__main__":
    main()