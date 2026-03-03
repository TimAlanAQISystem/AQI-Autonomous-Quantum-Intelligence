# pipeline/voice_spec.py

class VoiceSpec:
    def __init__(self, identity: str = "Confident Architect", pace_wpm: int = 150):
        self.identity = identity
        self.pace_wpm = pace_wpm

    def build_spec(self, timeline):
        return {
            "voice_identity": self.identity,
            "pace_wpm": self.pace_wpm,
            "segments": [
                {
                    "timestamp": seg["timestamp"],
                    "text": seg["text"],
                    "tone": "calm",
                    "emphasis": seg["emphasis"]
                }
                for seg in timeline
            ]
        }