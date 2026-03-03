import os

from aqi_core.governance import Governance
from pipeline.blueprint import MediaBlueprint
from pipeline.script_engine import ScriptTimeline
from pipeline.voice_spec import VoiceSpec
from pipeline.visual_composer import VisualComposer
from pipeline.render_planner import RenderPlanner
from pipeline.timeline_sync import TimelineSynchronizer
from pipeline.audio_spec import AudioMixSpec
from pipeline.output_spec import OutputSpecBuilder

from integrations.ffmpeg_video_renderer import FFmpegVideoRenderer
from integrations.ffmpeg_audio_mixer import FFmpegAudioMixer
from integrations.tts_interface import TextToSpeechEngine

def run_intro_video_with_real_tools(blueprint: MediaBlueprint, work_dir: str, governance: Governance):
    gov = governance

    # 1. Validate blueprint
    blueprint.validate()

    # 2. Script timeline
    timeline = ScriptTimeline(blueprint.script).generate_timeline()

    # 3. Voice spec + TTS
    voice_spec = VoiceSpec("Confident Architect", 150).build_spec(timeline)
    tts = TextToSpeechEngine()
    voice_audio_path = os.path.join(work_dir, "aqi_intro_voiceover.wav")
    tts.synthesize(voice_spec, voice_audio_path)

    # 4. Visual composition
    scene_specs = VisualComposer(blueprint.storyboard, blueprint.visual_style).build_scene_specs(timeline)

    # 5. Render planning + scenes
    render_plan = RenderPlanner().build_render_plan(scene_specs)
    renderer = FFmpegVideoRenderer()
    scenes_dir = os.path.join(work_dir, "scenes")
    rendered_scene_files = renderer.render_scenes(render_plan, scene_specs, scenes_dir)

    # 6. Timeline sync
    master_timeline = TimelineSynchronizer().build_master_timeline(scene_specs, voice_spec)

    # 7. Audio mix plan + mixing
    mix_plan = AudioMixSpec(blueprint.audio_style).build_mix_plan(voice_spec)
    mixer = FFmpegAudioMixer()
    final_audio_path = os.path.join(work_dir, "aqi_intro_audio_mix.wav")
    # Optional: pass a music track here
    mixer.mix(mix_plan, voice_audio_path, final_audio_path, music_path=None)

    # 8. Output spec
    output_spec = OutputSpecBuilder(blueprint.metadata).build_output_spec()
    final_video_path = os.path.join(work_dir, output_spec["output_file"] + ".mp4")

    # 9. Governance: block here unless steward has authorized
    gov.assert_can_publish()  # this will throw unless you explicitly authorize

    # 10. Assemble final video (FFmpeg concat of scenes + audio)
    concat_list_path = os.path.join(work_dir, "scenes.txt")
    with open(concat_list_path, "w") as f:
        for scene_file in rendered_scene_files:
            rel_path = os.path.relpath(scene_file, work_dir)
            f.write(f"file '{rel_path}'\n")

    # FFmpeg concat + audio overlay
    # Assumes all scenes have same resolution/codec
    import subprocess
    os.chdir(work_dir)  # Change to work dir for relative paths
    
    # First, concat just the videos
    video_cmd = [
        r"c:\Users\signa\OneDrive\Desktop\Agent X\aqi_media\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
    ]
    
    # Add all scene files as inputs
    for scene_file in rendered_scene_files:
        rel_path = os.path.relpath(scene_file, work_dir)
        video_cmd.extend(["-i", rel_path])
    
    # Build concat filter for video streams only
    num_scenes = len(rendered_scene_files)
    video_inputs = "".join([f"[{i}:v]" for i in range(num_scenes)])
    video_filter = f"{video_inputs}concat=n={num_scenes}:v=1:a=0[v]"
    
    temp_video = "temp_video.mp4"
    video_cmd.extend([
        "-filter_complex", video_filter,
        "-map", "[v]",
        "-c:v", "libx264",
        "-y", temp_video
    ])
    
    subprocess.run(video_cmd, check=True)
    
    # Then add audio
    audio_cmd = [
        r"c:\Users\signa\OneDrive\Desktop\Agent X\aqi_media\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
        "-i", temp_video,
        "-i", "aqi_intro_voiceover.wav",  # Use original voice instead of mixed
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-y", os.path.basename(final_video_path)
    ]
    
    subprocess.run(audio_cmd, check=True)
    
    # Clean up temp file
    if os.path.exists(temp_video):
        os.remove(temp_video)

    return {
        "final_video_path": final_video_path,
        "master_timeline": master_timeline,
        "output_spec": output_spec
    }

# Define the blueprint for the AQI intro video
script = """
Introducing AQI Autonomous Quantum Intelligence.

This is the beginning of a new era...

[Full script would go here]
"""

storyboard = [
    {"duration": 60, "description": "Intro scene with fluid lattice", "elements": [{"type": "text", "content": "Introducing AQI"}]},
    {"duration": 180, "description": "Problem demonstration", "elements": [{"type": "text", "content": "The Problem"}]},
    {"duration": 210, "description": "New category birth", "elements": [{"type": "text", "content": "New Category"}]},
    {"duration": 240, "description": "Necessity argument", "elements": [{"type": "text", "content": "Necessity"}]},
    {"duration": 180, "description": "Architecture of trust", "elements": [{"type": "text", "content": "Architecture"}]},
    {"duration": 210, "description": "World after AQI", "elements": [{"type": "text", "content": "World After"}]},
    {"duration": 120, "description": "Why now", "elements": [{"type": "text", "content": "Why Now"}]},
    {"duration": 60, "description": "Closing invitation", "elements": [{"type": "text", "content": "Invitation"}]}
]

visual_style = {
    "color": "deep blues/charcoals + gold/teal accents",
    "motion": "smooth, fluid transitions",
    "typography": "clean, modern, high contrast"
}

audio_style = {
    "voice": "confident, warm, non-hyped",
    "music": "minimalist, cinematic, 70-90 BPM"
}

metadata = {
    "title": "Why AQI Autonomous Quantum Intelligence Is No Longer Optional",
    "filename": "AQI_Intro_YouTube",
    "format": "mp4",
    "resolution": "1080p"
}

blueprint = MediaBlueprint(
    script=script,
    storyboard=storyboard,
    visual_style=visual_style,
    audio_style=audio_style,
    metadata=metadata,
    governance_id="AQI.Media.Intro.v1"
)

if __name__ == "__main__":
    work_dir = "output"
    os.makedirs(work_dir, exist_ok=True)
    
    # For testing: Authorize publishing
    gov = Governance()
    gov.authorize_publishing()
    print("Steward approval granted for testing.")
    
    try:
        result = run_intro_video_with_real_tools(blueprint, work_dir, gov)
        print(f"Video generated: {result['final_video_path']}")
    except Exception as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")