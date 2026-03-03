import pyttsx3
import threading
import time
import sys

# ==============================
# Alan Voice & Listener System (Demo Version)
# ==============================

# Global flags
listening_enabled = True      # Master listen toggle (can be turned off by voice/keyboard)
session_active = False        # True while you're in a "conversation" after he says "I'm here"
wake_word = "alan"            # What you say to get his attention
stop_listening_phrase = "alan stop listening"
start_listening_phrase = "alan start listening"
end_session_phrases = ["thank you alan", "ok alan", "that is all alan", "we are done alan"]

# Initialize TTS
engine = pyttsx3.init()
engine.setProperty('rate', 175)   # Adjust speaking speed
engine.setProperty('volume', 1.0) # Max volume


def speak(text: str):
    """Alan's voice output."""
    print(f"Alan: {text}")
    engine.say(text)
    engine.runAndWait()


def normalize_text(text: str) -> str:
    """Simple normalization to lower-case and strip spaces."""
    if not text:
        return ""
    return text.strip().lower()


def contains_phrase(text: str, phrase: str) -> bool:
    """Check if phrase is in text."""
    return phrase in normalize_text(text)


def any_phrase_in_text(text: str, phrases) -> bool:
    """Check if any of the phrases occur in text."""
    norm = normalize_text(text)
    return any(p in norm for p in phrases)


def get_user_input() -> str:
    """Get user input (simulating voice input for now)."""
    try:
        # For demo, we'll use keyboard input
        # In real implementation, this would be speech recognition
        user_input = input("You: ").strip()
        return user_input
    except KeyboardInterrupt:
        return "exit"
    except:
        return ""


def alan_main_loop():
    global listening_enabled, session_active

    speak("Alan listener initialized. Type your commands...")

    while True:
        if not listening_enabled:
            # When not listening, sleep lightly and periodically check flag
            print("Alan: Not listening (type 'alan start listening' to re-enable)")
            time.sleep(2.0)
            continue

        # Idle state: waiting for wake word or control phrase
        if not session_active:
            print("Alan idle: waiting for wake word or commands...")
            heard = get_user_input()

            if heard == "exit":
                speak("Goodbye.")
                break

            if not heard:
                continue

            print(f"Heard (idle): {heard}")

            # Stop listening command
            if contains_phrase(heard, stop_listening_phrase):
                listening_enabled = False
                speak("I will stop listening until you call me again.")
                continue

            # Start listening command (in case you re-enable via script logic later)
            if contains_phrase(heard, start_listening_phrase):
                listening_enabled = True
                speak("I am listening.")
                continue

            # Wake word to start a session
            if contains_phrase(heard, wake_word):
                session_active = True
                speak("I'm here.")
                continue

            # Otherwise ignore and remain idle
            speak("I didn't catch that. Say 'Alan' to get my attention.")
            continue

        # Session is active: you're talking to Alan
        if session_active:
            print("Alan session active: listening to you...")
            heard = get_user_input()

            if heard == "exit":
                speak("Goodbye.")
                break

            if not heard:
                # No clear input, just loop back
                continue

            print(f"Heard (session): {heard}")

            # Check for end-of-session phrases
            if any_phrase_in_text(heard, end_session_phrases):
                speak("Understood. I'll go back to idle.")
                session_active = False
                continue

            # Check for stop listening even during a session
            if contains_phrase(heard, stop_listening_phrase):
                listening_enabled = False
                session_active = False
                speak("I will stop listening until you call me again.")
                continue

            # Normal session behavior:
            # For now, he just acknowledges hearing you.
            # This is where you can later plug in actual processing logic.
            speak("I hear you.")


def main():
    print("=" * 50)
    print("ALAN VOICE LISTENER DEMO")
    print("=" * 50)
    print("This is a keyboard-based demo of the Alan listener system.")
    print("In the full version, this will use speech recognition.")
    print("")
    print("Commands:")
    print("- Say 'Alan' to start a session")
    print("- Say 'thank you alan', 'ok alan', etc. to end session")
    print("- Say 'alan stop listening' to disable completely")
    print("- Type 'exit' to quit")
    print("=" * 50)

    # Run in main thread so audio works reliably
    alan_main_loop()


if __name__ == "__main__":
    main()