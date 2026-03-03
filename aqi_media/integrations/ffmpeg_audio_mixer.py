import subprocess
from typing import Dict, Optional

class FFmpegAudioMixer:
    def __init__(self, ffmpeg_path: str = "c:\\Users\\signa\\OneDrive\\Desktop\\Agent X\\aqi_media\\ffmpeg\\ffmpeg-8.0.1-essentials_build\\bin\\ffmpeg.exe"):
        self.ffmpeg_path = ffmpeg_path

    def mix(self, mix_plan: Dict, voice_audio_path: str, output_path: str, music_path: Optional[str] = None):
        """
        mix_plan:
          - tracks: [{type: "voice"/"music", gain_db: -3}, ...]
        """
        # Extract gains
        voice_gain = 0
        music_gain = 0

        for track in mix_plan.get("tracks", []):
            if track["type"] == "voice":
                voice_gain = track.get("gain_db", 0)
            elif track["type"] == "music":
                music_gain = track.get("gain_db", 0)

        if music_path:
            # Two-track mix: voice + music
            filter_complex = (
                f"[0:a]volume={10 ** (voice_gain / 20.0)}[voice];"
                f"[1:a]volume={10 ** (music_gain / 20.0)}[music];"
                "[voice][music]amix=inputs=2:duration=longest"
            )

            cmd = [
                self.ffmpeg_path,
                "-i", voice_audio_path,
                "-i", music_path,
                "-filter_complex", filter_complex,
                "-c:a", "aac",
                "-y", output_path
            ]
        else:
            # Voice-only, gain-adjusted
            filter_complex = f"volume={10 ** (voice_gain / 20.0)}"
            cmd = [
                self.ffmpeg_path,
                "-i", voice_audio_path,
                "-filter:a", filter_complex,
                "-c:a", "aac",
                "-y", output_path
            ]

        subprocess.run(cmd, check=True)
        return output_path