# integrations/audio_mixer_interface.py

class AudioMixerEngine:
    def mix(self, mix_plan, voice_audio_path: str, output_path: str):
        """
        Abstract interface for audio mixing.
        - mix_plan: dict from AudioMixSpec.build_mix_plan()
        - voice_audio_path: path to voiceover audio file
        - output_path: path for final mixed audio

        Implementation must:
          - generate a mixed audio file at output_path
        """
        raise NotImplementedError("Audio mixer integration not implemented.")