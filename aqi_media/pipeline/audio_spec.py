# pipeline/audio_spec.py

class AudioMixSpec:
    def __init__(self, music_profile=None):
        self.music_profile = music_profile or {"style": "minimal_cinematic", "target_lufs": -18}

    def build_mix_plan(self, voice_spec):
        return {
            "tracks": [
                {"type": "voice", "gain_db": -3},
                {"type": "music", "gain_db": -18}
            ],
            "voice_spec": voice_spec,
            "music_profile": self.music_profile,
            "export_format": "wav"
        }