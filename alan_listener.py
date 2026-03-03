import speech_recognition as sr
import pyttsx3
import threading
import time
import random

# ==============================
# Alan Voice & Listener System
# ==============================

# Global flags
listening_enabled = True      # Master listen toggle (can be turned off by voice)
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


def listen_once(recognizer: sr.Recognizer) -> str:
    """Listen once and return recognized text, or empty string on failure."""
    try:
        # Use Windows default microphone without pyaudio
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, phrase_time_limit=6)
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        # Network issue or Google API problem
        return ""
    except Exception as e:
        print(f"Listening error: {e}")
        return ""


def get_response(text: str) -> str:
    """Generate a response based on input."""
    responses = [
        "I understand.",
        "Got it.",
        "Understood.",
        "I see.",
        "Okay.",
        "Alright.",
        "Yes.",
        "Sure."
    ]
    return random.choice(responses)


def alan_main_loop():
    global listening_enabled, session_active

    recognizer = sr.Recognizer()

    speak("Alan listener initialized.")

    while True:
        if not listening_enabled:
            # When not listening, sleep lightly and periodically check flag
            time.sleep(1.0)
            continue

        # Idle state: waiting for wake word or control phrase
        if not session_active:
            print("Alan idle: listening for wake word or commands...")
            heard = listen_once(recognizer)

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
            continue

        # Session is active: you're talking to Alan
        if session_active:
            print("Alan session active: listening to you...")
            heard = listen_once(recognizer)

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
            response = get_response(heard)
            speak(response)


def main():
    # Run in main thread so audio works reliably
    alan_main_loop()


if __name__ == "__main__":
    main()