"""
voice_tts plugin for Agent X
Enhanced with professional voice settings for natural human-like conversations
Usage via plugin_system:
  call_plugin_with_timeout("voice_tts", text="Hello", rate=180, timeout=8)
"""
from typing import Dict, Any


def schema() -> Dict[str, Any]:
    return {
        "name": "voice_tts",
        "description": "Speak text using system TTS with professional voice optimization",
        "args": {
            "text": {"type": "string", "required": True},
            "rate": {"type": "integer", "required": False, "default": 160},
            "volume": {"type": "float", "required": False, "default": 0.9},
            "voice_name": {"type": "string", "required": False, "default": None},
        },
    }


def run(text: str, rate: int = 160, volume: float = 0.9, voice_name: str = None) -> Dict[str, Any]:
    """
    Enhanced TTS with professional voice settings for natural conversations
    """
    try:
        import pyttsx3
    except Exception:
        return {"ok": False, "error": "TTS unavailable. Install 'pyttsx3' to enable voice output."}

    try:
        engine = pyttsx3.init()

        # Get available voices for selection
        voices = engine.getProperty('voices')

        # Select best professional voice if not specified
        if voice_name:
            selected_voice = None
            for voice in voices:
                if voice_name.lower() in voice.name.lower():
                    selected_voice = voice
                    break
        else:
            selected_voice = select_professional_voice(voices)

        if selected_voice:
            engine.setProperty('voice', selected_voice.id)
            print(f"🎙️ Using voice: {selected_voice.name}")

        # Optimize voice settings for natural human-like speech
        engine.setProperty('rate', int(rate))  # 160 WPM default (professional pace)
        engine.setProperty('volume', float(volume))  # 0.9 default (clear but not aggressive)

        # Add natural speech enhancements
        enhanced_text = add_natural_delivery(text)

        print(f"🎙️ Speaking: {enhanced_text[:60]}...")
        engine.say(enhanced_text)
        engine.runAndWait()

        return {
            "ok": True,
            "voice": selected_voice.name if selected_voice else "default",
            "rate": rate,
            "volume": volume
        }

    except Exception as e:
        return {"ok": False, "error": f"TTS error: {e}"}


def select_professional_voice(voices):
    """
    Select the best professional voice for natural conversations
    Prioritizes voices that sound natural and professional
    """
    # Preferred professional voices (in order of preference)
    preferred_voices = [
        'Microsoft David Desktop',   # Professional male (Alan)
        'Microsoft Mark Desktop',    # Natural male
        'Microsoft Zira Desktop',    # Professional female, very natural
        'Microsoft Hazel Desktop',   # Warm, natural female
        'Microsoft Catherine Desktop', # Clear female
        'SAPI5 Voice',              # Fallback
    ]

    # Try to find preferred voices
    for preferred in preferred_voices:
        for voice in voices:
            if preferred.lower() in voice.name.lower():
                return voice

    # Fallback: prefer male voices for Alan
    male_voices = [v for v in voices if 'male' in v.name.lower() or 'david' in v.name.lower() or 'mark' in v.name.lower()]
    if male_voices:
        return male_voices[0]

    # Ultimate fallback: first available voice
    return voices[0] if voices else None


def add_natural_delivery(text: str) -> str:
    """
    Add natural speech patterns and pauses for human-like delivery
    """
    # Add natural pauses after greetings
    text = text.replace("Hello", "Hello...")
    text = text.replace("Hi", "Hi...")

    # Add emphasis on important conversational elements
    emphasis_words = [
        "absolutely", "certainly", "definitely", "exactly", "perfect",
        "great", "excellent", "wonderful", "fantastic", "amazing",
        "understand", "appreciate", "thank you", "please", "sure"
    ]

    # Add slight pauses before questions
    text = text.replace("?", "...?")

    # Add natural flow pauses at commas and periods
    text = text.replace(",", ", ")
    text = text.replace(".", ". ")

    return text


"""
Text-to-Speech plugin using pyttsx3 (optional)
Install: pip install pyttsx3
"""
def run_legacy(*args, **kwargs):
    text = kwargs.get('text') or "Hello from Agent X"
    rate = kwargs.get('rate') or 160
    try:
        import pyttsx3
    except Exception:
        return "TTS unavailable. Install 'pyttsx3' to enable voice output."

    try:
        engine = pyttsx3.init()

        # Use enhanced settings
        voices = engine.getProperty('voices')
        selected_voice = select_professional_voice(voices)
        if selected_voice:
            engine.setProperty('voice', selected_voice.id)

        engine.setProperty('rate', int(rate))
        engine.setProperty('volume', 0.9)

        enhanced_text = add_natural_delivery(text)

        engine.say(enhanced_text)
        engine.runAndWait()
        return "Speaking now with natural voice."
    except Exception as e:
        return f"TTS error: {e}"


def get_info():
    return {
        "name": "voice_tts",
        "version": "2.0",
        "description": "Enhanced TTS with professional voice optimization for natural conversations",
        "requires": ["pyttsx3"],
        "schema": {
            "kwargs": {
                "text": {"type": "string", "required": True},
                "rate": {"type": "integer", "required": False, "default": 160},
                "volume": {"type": "float", "required": False, "default": 0.9},
                "voice_name": {"type": "string", "required": False}
            }
        },
        "features": [
            "Professional voice selection",
            "Natural speech pacing (160 WPM)",
            "Optimized volume (90%)",
            "Natural delivery enhancements",
            "Multiple voice options"
        ]
    }
