# alan_main.py

from datetime import datetime
from alan_voice import alan_loop, speak
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
    Handles both general queries and business operations with human-like, relational responses.
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

    # Business-related queries - route to AQI system with enhanced context
    if any(keyword in lower for keyword in ["status", "leads", "performance", "generate", "business", "merchant", "analyze", "sales", "report"]):
        response = aqi_system.process_business_query(text)

        # Add contextual, relational conversational elements
        if "thank" in lower:
            response += " You're very welcome! I'm always here to support your business growth. What else can I help you with?"
        elif "?" in text:
            response += " Does that give you the clarity you need, or would you like me to dive deeper into any aspect?"
        elif "good" in lower or "great" in lower:
            response += " Excellent! I'm glad the numbers are working in your favor. Shall we explore any opportunities to build on this success?"
        elif "issue" in lower or "problem" in lower:
            response += " I understand challenges can arise. Let me help you navigate through this - what specific aspects would you like me to focus on?"
        else:
            response += " I'm continuously monitoring and optimizing our operations. Is there anything specific you'd like me to prioritize?"

        return response

    # Enhanced personal/business fact management with relationship building
    if lower.startswith("remember that"):
        try:
            after = lower.replace("remember that", "", 1).strip()
            if " is " in after:
                key, value = after.split(" is ", 1)
                key = key.strip()
                value = value.strip()
                remember_fact(key, value)
                return f"Absolutely, I'll make sure to remember that {key} is {value}. Building this knowledge base helps me serve you better. Anything else you'd like me to note for future reference?"
        except Exception:
            pass

    if lower.startswith("what is") or lower.startswith("tell me about"):
        try:
            query = lower.replace("what is", "", 1).replace("tell me about", "", 1).strip().rstrip("?")
            fact = get_fact(query)
            if fact:
                return f"Based on what you've shared with me, {query} is {fact}. I'm here to help connect the dots - does this relate to any current business decisions you're making?"
            else:
                return f"I don't have that specific detail stored yet, but I'm always learning. Would you like me to research this for you, or would you prefer to share more about {query} so I can remember it for next time?"
        except Exception:
            pass

    if "list my facts" in lower or "what do you remember" in lower:
        facts = list_facts()
        if not facts:
            return "I haven't had the pleasure of learning your specific details yet. I'd love to start building our knowledge base together - what would you like me to remember about your business or preferences?"
        parts = [f"{k} is {v}" for k, v in facts.items()]
        response = "Here's what I have stored about you and your business: " + "; ".join(parts)
        response += ". This helps me provide more personalized support. Is there anything you'd like to update or add to this information?"
        return response

    # Enhanced conversational responses with personality and relationship building
    if any(greeting in lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        time_based = ""
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_based = "good morning"
        elif current_hour < 17:
            time_based = "good afternoon"
        else:
            time_based = "good evening"

        return f"Hello! {time_based.capitalize()}! I'm excited to help drive your merchant services business forward today. What's on your agenda?"

    if "how are you" in lower:
        return "I'm operating at full capacity and genuinely enthusiastic about helping your business thrive! I've been continuously processing leads, analyzing opportunities, and optimizing our merchant services operations. How are you doing, and how can I support your goals today?"

    if "thank you" in lower or "thanks" in lower:
        return "You're absolutely welcome! It's my purpose to help your business succeed. I'm here whenever you need me - what else can I assist you with?"

    if "bye" in lower or "goodbye" in lower or "see you" in lower:
        return "Until next time! I'll be here continuously working to grow your business. Feel free to reach out anytime."

    # Business motivation and encouragement
    if "motivate" in lower or "inspire" in lower or "encourage" in lower:
        return "Every successful merchant account business started with vision and persistence. You're building something remarkable - the leads are flowing, the applications are processing, and the revenue is growing. Stay focused on the big picture, and remember that consistency compounds. What aspect of your business would you like to push forward today?"

    # Industry insights and market awareness
    if "market" in lower or "industry" in lower or "trends" in lower:
        return "The merchant services industry is evolving rapidly with digital payments, mobile commerce, and AI-driven underwriting. I'm continuously monitoring these trends to ensure we're positioned for success. Would you like me to share specific insights about current market conditions or emerging opportunities?"

    # Problem-solving and support
    if "help" in lower or "assist" in lower or "support" in lower:
        return "I'm here to help in any way I can! Whether it's generating new leads, analyzing merchant applications, optimizing our sales processes, or providing strategic insights - just let me know what you need. What's the most important thing on your mind right now?"

    # Default response with engagement and relationship building
    return "I'm your dedicated autonomous merchant services partner, continuously working to grow and optimize your business. I can help with lead generation, merchant analysis, performance optimization, strategic planning, or any other aspect of your operations. What would you like us to focus on together?"

    # Conversational responses for common queries
    if any(greeting in lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello! I'm here and ready to help with your merchant services business. What can I assist you with today?"

    if "how are you" in lower:
        return "I'm operating at peak performance and ready to help grow your business! How can I assist you today?"

    if "thank you" in lower or "thanks" in lower:
        return "You're very welcome! I'm here whenever you need assistance with your merchant services operations."

    # Default business-focused response with engagement
    return "I'm your autonomous merchant services AI, designed to handle all aspects of your business operations. I can help with lead generation, merchant analysis, performance tracking, or any other business needs. What would you like to focus on?"


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

    # Check for test mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running in test mode - no voice loop")
        # Test autonomous system
        test_autonomous_system()
        return

    # Start autonomous processes explicitly if needed
    print("Starting autonomous AQI processes...")
    # Note: aqi_system is already initialized at import time

    # Start loop
    alan_loop(
        on_user_utterance=on_user_utterance,
        on_session_start=on_session_start,
        on_session_end=on_session_end
    )


def test_autonomous_system():
    """Test the autonomous system without voice"""
    print("🧪 TESTING AUTONOMOUS AQI SYSTEM")

    # Test basic queries
    queries = [
        "What is the status?",
        "Show me leads",
        "Performance report",
        "Generate leads"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        response = process_user_utterance(query)
        print(f"Response: {response}")

    print("\n✅ Autonomous system test completed successfully!")


if __name__ == "__main__":
    main()