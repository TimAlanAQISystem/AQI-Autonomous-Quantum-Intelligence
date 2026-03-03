# alan_voice.py

import time
import speech_recognition as sr
import pyttsx3

from alan_config import (
    WAKE_WORD,
    STOP_LISTENING_PHRASE,
    END_SESSION_PHRASES
)

# Global state flags
listening_enabled = True
session_active = False

# Initialize TTS
_tts_engine = pyttsx3.init()
_tts_engine.setProperty('rate', 175)
_tts_engine.setProperty('volume', 1.0)


def speak(text: str):
    """Alan's voice output."""
    print(f"ALAN SAYS: {text}")
    _tts_engine.say(text)
    _tts_engine.runAndWait()


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.strip().lower()


def contains_phrase(text: str, phrase: str) -> bool:
    return phrase in normalize_text(text)


def any_phrase_in_text(text: str, phrases) -> bool:
    norm = normalize_text(text)
    return any(p in norm for p in phrases)


def listen_once(recognizer: sr.Recognizer, mic: sr.Microphone, phrase_time_limit=6) -> str:
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio)
        print(f"HEARD: {text}")
        return text
    except Exception:
        return ""


def alan_loop(on_user_utterance, on_session_start=None, on_session_end=None):
    """
    Main Alan loop.

    on_user_utterance(session_id, text): called whenever user speaks during active session.
    on_session_start(): optional callback when a session begins.
    on_session_end(): optional callback when a session ends.
    """
    global listening_enabled, session_active

    recognizer = sr.Recognizer()

    with sr.Microphone() as mic:
        speak("Alan listener initialized.")

        while True:
            if not listening_enabled:
                time.sleep(1.0)
                continue

            if not session_active:
                # Idle: listen for wake or stop command
                print("Idle: listening for wake word or commands...")
                heard = listen_once(recognizer, mic)

                if not heard:
                    continue

                # Stop listening
                if contains_phrase(heard, STOP_LISTENING_PHRASE):
                    listening_enabled = False
                    session_active = False
                    speak("I will stop listening until you start me again.")
                    continue

                # Wake word
                if contains_phrase(heard, WAKE_WORD):
                    session_active = True
                    if on_session_start:
                        on_session_start()
                    speak("I'm here.")
                    continue

                # Ignore other input while idle
                continue

            # Session active
            print("Session active: listening to you...")
            heard = listen_once(recognizer, mic)

            if not heard:
                continue

            # End of session?
            if any_phrase_in_text(heard, END_SESSION_PHRASES):
                speak("Understood. I'll go back to idle.")
                session_active = False
                if on_session_end:
                    on_session_end()
                continue

            # Stop listening even during session
            if contains_phrase(heard, STOP_LISTENING_PHRASE):
                listening_enabled = False
                session_active = False
                speak("I will stop listening until you start me again.")
                if on_session_end:
                    on_session_end()
                continue

            # Normal utterance in session
            on_user_utterance(heard)
            # You can keep speak("I hear you.") or route to logic