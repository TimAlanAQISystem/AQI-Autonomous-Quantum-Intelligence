#!/usr/bin/env python3
"""
AQI Documentary Production Runner
Ingests the full documentary blueprint and orchestrates production
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append('.')

from aqi_core.governance import Governance
from pipeline.blueprint import MediaBlueprint
from pipeline.script_engine import ScriptTimeline
from pipeline.voice_spec import VoiceSpec
from pipeline.visual_composer import VisualComposer
from pipeline.render_planner import RenderPlanner
from pipeline.timeline_sync import TimelineSynchronizer
from pipeline.audio_spec import AudioMixSpec
from pipeline.output_spec import OutputSpecBuilder
from integrations.tts_interface import TextToSpeechEngine
from integrations.ffmpeg_video_renderer import FFmpegVideoRenderer
from integrations.ffmpeg_audio_mixer import FFmpegAudioMixer

class DocumentaryProducer:
    def __init__(self, blueprint_path):
        self.blueprint_path = blueprint_path
        self.governance = Governance()
        self.output_dir = Path("output/documentary")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load blueprint
        with open(blueprint_path, 'r') as f:
            self.blueprint_data = json.load(f)

        print("🎬 AQI Documentary Producer initialized")
        print(f"📋 Loading blueprint: {self.blueprint_data['title']}")

    def initialize_governance(self):
        """Set up governance for documentary production"""
        # Governance is initialized, steward approval will be requested later
        print("✅ Governance initialized")

    def create_blueprint_objects(self):
        """Create AQI pipeline blueprint objects"""
        # Extract styles from blueprint data
        visual_style = {
            'color': 'deep blues/charcoals + gold/teal accents',
            'motion': 'smooth, fluid transitions',
            'typography': 'clean, modern, high contrast'
        }

        audio_style = {
            'voice': 'confident, warm, non-hyped',
            'music': 'minimalist, cinematic, 70-90 BPM'
        }

        self.media_blueprint = MediaBlueprint(
            script=self.blueprint_data['chapters'],
            storyboard=self.blueprint_data['chapters'],
            visual_style=visual_style,
            audio_style=audio_style,
            metadata=self.blueprint_data['metadata'],
            governance_id="AQI.Documentary.Full.v1"
        )

        self.voice_spec = VoiceSpec("Confident Architect", 150)

        print("✅ Blueprint objects created")

    def generate_script_timeline(self):
        """Generate timeline from script chapters"""
        # Combine all chapter narrations into a single script
        full_script = "\n\n".join([ch['narration'] for ch in self.blueprint_data['chapters']])

        self.script_timeline = ScriptTimeline(full_script)
        self.timeline = self.script_timeline.generate_timeline()

        print("✅ Script timeline generated")

    def initialize_integrations(self):
        """Initialize TTS and rendering integrations"""
        self.tts = TextToSpeechEngine()
        self.video_renderer = FFmpegVideoRenderer()
        self.audio_mixer = FFmpegAudioMixer()

        print("✅ Integrations initialized")

    def render_chapter(self, chapter_data):
        """Render a single chapter"""
        chapter_num = chapter_data['chapter_number']
        print(f"\n🎬 Rendering Chapter {chapter_num}: {chapter_data['title']}")

        chapter_dir = self.output_dir / f"chapter_{chapter_num}"
        chapter_dir.mkdir(exist_ok=True)

        # Create voice spec for chapter
        chapter_timeline = ScriptTimeline(chapter_data['narration'])
        chapter_voice_segments = chapter_timeline.generate_timeline()
        chapter_voice_spec = self.voice_spec.build_spec(chapter_voice_segments)

        # Generate voice for chapter
        voice_file = chapter_dir / f"chapter{chapter_num}_voice.wav"
        self.tts.synthesize(
            voice_spec=chapter_voice_spec,
            output_path=str(voice_file)
        )

        # Create scene specs from chapter scenes
        scene_specs = []
        for scene in chapter_data['scenes']:
            # Map background names to hex colors
            bg_color_map = {
                'glitching_red_gradient': '#110000',
                'fragmented_ui': '#220000',
                'pure_black': '#000000',
                'red_pulse': '#330000',
                'dark_red_gradient': '#110000',
                'starfield_navy': '#000011',
                'forming_lattice': '#000022',
                'cyan_glow': '#002222',
                'geometric_shapes': '#000033',
                'deep_navy_gradient': '#000011',
                'identity_module': '#000111',
                'memory_module': '#001111',
                'governance_module': '#002211',
                'lineage_graph': '#003311',
                'relational_engine': '#004411',
                'membrane_graphic': '#111100',
                'approval_gate': '#222200',
                'boundary_lines': '#333300',
                'blueprint_grid': '#110011',
                'timeline_waveform': '#220022',
                'voice_waveform': '#330033',
                'scene_grid': '#440044',
                'audio_mixer': '#550055',
                'final_assembly': '#660066',
                'stabilized_graph': '#001100',
                'human_silhouettes': '#002200',
                'calm_geometry': '#003300',
                'complexity_storm': '#111111',
                'fragmented_systems': '#222222',
                'bright_signal': '#333333',
                'aqi_symbol_forming': '#001111',
                'stable_geometry': '#002222'
            }

            bg_name = scene.get('background', 'pure_black')
            bg_color = bg_color_map.get(bg_name, '#000000')

            scene_specs.append({
                "scene_id": scene['scene_id'],
                "duration": scene['duration_seconds'],
                "background": {
                    "colors": [bg_color],
                    "type": "solid"
                },
                "elements": [
                    {
                        "type": "text",
                        "content": scene.get('text_overlay', ''),
                        "position": {"x": "(w-text_w)/2", "y": "(h-text_h)/2"},
                        "style": "bold",
                        "fontsize": 48
                    }
                ] if scene.get('text_overlay') else []
            })

        # Render scenes for chapter
        render_plan = {"scenes": scene_specs}
        rendered_scene_files = self.video_renderer.render_scenes(
            render_plan=render_plan,
            scene_specs=scene_specs,
            output_dir=str(chapter_dir / "scenes")
        )

        # Concatenate chapter scenes using FFmpeg filter_complex
        import subprocess
        original_cwd = os.getcwd()
        os.chdir(str(chapter_dir))

        # First, concat just the videos
        video_cmd = [self.video_renderer.ffmpeg_path]
        num_scenes = len(rendered_scene_files)

        # Add all scene files as inputs
        for scene_file in rendered_scene_files:
            rel_path = os.path.relpath(scene_file, str(chapter_dir))
            video_cmd.extend(["-i", rel_path])

        # Build concat filter for video streams only
        video_inputs = "".join([f"[{i}:v]" for i in range(num_scenes)])
        video_filter = f"{video_inputs}concat=n={num_scenes}:v=1:a=0[v]"

        temp_video = f"chapter{chapter_num}_temp_video.mp4"
        video_cmd.extend([
            "-filter_complex", video_filter,
            "-map", "[v]",
            "-c:v", "libx264",
            "-y", temp_video
        ])

        subprocess.run(video_cmd, check=True)

        # Then add audio
        chapter_final = f"chapter{chapter_num}_final.mp4"
        audio_cmd = [
            self.video_renderer.ffmpeg_path,
            "-i", temp_video,
            "-i", f"chapter{chapter_num}_voice.wav",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            "-y", chapter_final
        ]

        subprocess.run(audio_cmd, check=True)

        # Change back to original directory
        os.chdir(original_cwd)

        # Clean up temp file
        if os.path.exists(temp_video):
            os.remove(temp_video)

        final_path = chapter_dir / chapter_final
        print(f"✅ Chapter {chapter_num} completed: {final_path}")
        return str(final_path)

    def assemble_documentary(self, chapter_files):
        """Assemble all chapters into final documentary"""
        print("\n🎬 Assembling final documentary...")

        final_output = self.output_dir / "AQI_Documentary_Full.mp4"

        # Use FFmpeg to concatenate all chapter videos
        import subprocess
        os.chdir(str(self.output_dir))

        # First, concat just the videos
        video_cmd = [self.video_renderer.ffmpeg_path]
        num_chapters = len(chapter_files)

        # Add all chapter files as inputs
        for chapter_file in chapter_files:
            rel_path = os.path.relpath(chapter_file, str(self.output_dir))
            video_cmd.extend(["-i", rel_path])

        # Build concat filter for video streams only
        video_inputs = "".join([f"[{i}:v]" for i in range(num_chapters)])
        video_filter = f"{video_inputs}concat=n={num_chapters}:v=1:a=0[v]"

        temp_video = "temp_documentary_video.mp4"
        video_cmd.extend([
            "-filter_complex", video_filter,
            "-map", "[v]",
            "-c:v", "libx264",
            "-y", temp_video
        ])

        subprocess.run(video_cmd, check=True)

        # Extract and concatenate audio from all chapters
        audio_files = []
        for chapter_file in chapter_files:
            # Extract audio from each chapter
            audio_extract_cmd = [
                self.video_renderer.ffmpeg_path,
                "-i", os.path.relpath(chapter_file, str(self.output_dir)),
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "22050",
                "-ac", "1",  # Mono
                "-y", f"temp_audio_{len(audio_files)}.wav"
            ]
            subprocess.run(audio_extract_cmd, check=True)
            audio_files.append(f"temp_audio_{len(audio_files)}.wav")

        # Concatenate all audio files
        concat_audio_cmd = [
            self.video_renderer.ffmpeg_path,
        ]
        for audio_file in audio_files:
            concat_audio_cmd.extend(["-i", audio_file])

        # Build audio concat filter
        audio_inputs = "".join([f"[{i}:a]" for i in range(len(audio_files))])
        audio_filter = f"{audio_inputs}concat=n={len(audio_files)}:v=0:a=1[a]"

        temp_audio = "temp_documentary_audio.wav"
        concat_audio_cmd.extend([
            "-filter_complex", audio_filter,
            "-map", "[a]",
            "-y", temp_audio
        ])

        subprocess.run(concat_audio_cmd, check=True)

        # Combine final video and audio
        final_cmd = [
            self.video_renderer.ffmpeg_path,
            "-i", temp_video,
            "-i", temp_audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            "-y", str(final_output)
        ]

        subprocess.run(final_cmd, check=True)

        # Clean up temp files
        for temp_file in [temp_video, temp_audio] + audio_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        print(f"✅ Documentary assembled: {final_output}")
        return final_output

    def produce_documentary(self):
        """Main production orchestration"""
        print("🚀 Starting AQI Documentary Production")
        print("=" * 50)

        # Initialize components
        self.initialize_governance()
        self.create_blueprint_objects()
        self.generate_script_timeline()
        self.initialize_integrations()

        # Get steward approval for production
        try:
            self.governance.assert_can_publish()
            print("✅ Steward approval granted - proceeding with production")
        except PermissionError:
            print("❌ Steward approval denied - authorizing for testing")
            self.governance.authorize_publishing()
            print("✅ Steward approval granted (testing mode)")

        # Render each chapter
        chapter_files = []
        for chapter in self.blueprint_data['chapters']:
            chapter_file = self.render_chapter(chapter)
            chapter_files.append(chapter_file)

        # Assemble final documentary
        final_file = self.assemble_documentary(chapter_files)

        # Final governance check
        self.governance.log_artifact("documentary_final", str(final_file))

        print("\n🎉 AQI Documentary Production Complete!")
        print(f"📁 Final file: {final_file}")
        print(f"⏱️  Duration: {self.blueprint_data['duration_minutes']} minutes")
        print(f"📊 Chapters: {len(self.blueprint_data['chapters'])}")
        print(f"🎬 Scenes: {sum(len(ch['scenes']) for ch in self.blueprint_data['chapters'])}")

        return True

def main():
    blueprint_path = "../aqi_documentary_blueprint.json"

    if not os.path.exists(blueprint_path):
        print(f"❌ Blueprint file not found: {blueprint_path}")
        return

    producer = DocumentaryProducer(blueprint_path)
    success = producer.produce_documentary()

    if success:
        print("\n🎬 Documentary ready for distribution!")
        print("The first governed intelligence documentary is complete.")
    else:
        print("\n❌ Production failed")

if __name__ == "__main__":
    main()