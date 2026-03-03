# alan_voice_sounddevice.py

"""
Alternative voice module using sounddevice instead of PyAudio.
This avoids PyAudio installation issues on some systems.
"""

import time
import io
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
import numpy as np
import os
import soundfile as sf
import sys
import random
sys.path.append('../')
from aqi_elevenlabs_tts import ElevenLabsTTS

# AQI Quantum-Optimized Voice Library
AQI_VOICES = {
    "adam": "EXAVITQu4vr4xnSDxMaL",
    "antoni": "ErXwobaYiN019PkySvjV",
    "arnold": "VR6AewLTigWG4xSOukaG",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
    "sam": "yoZ06aMxZJJ28mfd3POQ",
    "drew": "29vD33N1CtxCmqQRPOHJ"
}

# Quiet Mode: Mutes AQI voice to avoid interruptions
QUIET_MODE = True

from alan_config import (
    WAKE_WORD,
    STOP_LISTENING_PHRASE,
    END_SESSION_PHRASES
)

# Global state flags
listening_enabled = True
session_active = False

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16

# Initialize TTS
_tts_engine = pyttsx3.init()
_tts_engine.setProperty('rate', 175)
_tts_engine.setProperty('volume', 1.0)


def speak(text: str):
    """Alan's voice output using AQI quantum-optimized ElevenLabs voices."""
    if QUIET_MODE:
        print(f"[QUIET MODE] Alan would say: {text}")
        return
    print(f"ALAN SAYS: {text}")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if api_key:
        # Quantum-optimized voice selection: random for variety, or based on AQI processing
        voice_name = random.choice(list(AQI_VOICES.keys()))
        voice_id = AQI_VOICES[voice_name]
        print(f"Using AQI voice: {voice_name}")
        tts = ElevenLabsTTS(api_key, voice_id=voice_id)
        path = tts.synthesize(text, "temp_alan.wav")
        if path:
            try:
                data, samplerate = sf.read(path)
                sd.play(data, samplerate)
                sd.wait()
                os.remove(path)  # Clean up
                return
            except Exception as e:
                print(f"Playback error: {e}")
    # Fallback to pyttsx3
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


def record_audio(duration=5, sample_rate=SAMPLE_RATE) -> bytes:
    """Record audio using sounddevice."""
    print(f"Recording for {duration} seconds...")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=CHANNELS, dtype=DTYPE)
    sd.wait()  # Wait for recording to finish

    # Convert to bytes in WAV format
    import wave
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return buffer.getvalue()


def listen_once(duration=5) -> str:
    """Listen once using sounddevice and return recognized text."""
    try:
        # Record audio
        audio_bytes = record_audio(duration)

        # Create AudioData object for speech_recognition
        audio_data = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)  # 2 bytes per sample

        # Recognize
        recognizer = sr.Recognizer()
        text = recognizer.recognize_google(audio_data)
        print(f"HEARD: {text}")
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return ""
    except Exception as e:
        print(f"Audio recording error: {e}")
        return ""


def alan_loop(on_user_utterance, on_session_start=None, on_session_end=None):
    """
    Main Alan loop using sounddevice.

    on_user_utterance(text): called whenever user speaks during active session.
    on_session_start(): optional callback when a session begins.
    on_session_end(): optional callback when a session ends.
    """
    global listening_enabled, session_active

    speak("Alan listener initialized with sounddevice.")

    while True:
        if not listening_enabled:
            time.sleep(1.0)
            continue

        if not session_active:
            # Idle: listen for wake or stop command
            print("Idle: listening for wake word or commands...")
            heard = listen_once(4)  # Shorter duration for wake word detection

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
        heard = listen_once(6)  # Longer duration for conversation

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