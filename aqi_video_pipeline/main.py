from aqi_core.governance import Governance
from ingestion.ingest_blueprint import BlueprintIngestion
from script_engine.script_timeline import ScriptTimeline
from voice_engine.voice_synth import VoiceSynth
from visual_composer.scene_builder import SceneBuilder
from renderer.scene_renderer import SceneRenderer
from timeline.sync_timeline import TimelineSynchronizer
from audio_mixer.mixer import AudioMixer
from final_output.render_package import RenderPackage

def run_pipeline(blueprint):
    gov = Governance()

    print("🚀 Starting AQI Video Pipeline Simulation")
    print("=" * 50)

    # 1. Ingest
    print("1. Ingesting blueprint...")
    ingestion = BlueprintIngestion(blueprint)
    ingestion.validate()
    internal = ingestion.produce_internal_representation()

    # 2. Script timeline
    print("2. Generating script timeline...")
    timeline = ScriptTimeline(internal["script"]).generate_timeline()

    # 3. Voice synthesis
    print("3. Synthesizing voice...")
    voice = VoiceSynth("Confident Architect").synthesize(timeline)

    # 4. Visual composition
    print("4. Building scene specifications...")
    scenespecs = SceneBuilder(internal["storyboard"]).build_scenes()

    # 5. Render scenes
    print("5. Rendering scenes...")
    renderer = SceneRenderer()
    rendered_scenes = [renderer.render(s) for s in scenespecs]

    # 6. Sync timeline
    print("6. Synchronizing timeline...")
    master_timeline = TimelineSynchronizer().sync(rendered_scenes, voice)

    # 7. Mix audio
    print("7. Mixing audio...")
    final_audio = AudioMixer().mix(voice)

    # 8. Package final output
    print("8. Packaging final video...")
    final_video = RenderPackage().package(rendered_scenes, final_audio, internal["metadata"])

    # Governance check
    print("9. Checking governance...")
    gov.require_steward_approval()

    print("=" * 50)
    print(f"🎉 Pipeline complete! Output: {final_video}")
    return final_video

# Test blueprint for simulation
test_blueprint = {
    "script": "Most people think intelligence is something you use.\nAQI is something you build a relationship with.\nThis is AQI Autonomous Quantum Intelligence.",
    "storyboard": ["Opening scene", "Reveal scene", "Closing scene"],
    "metadata": {"title": "AQI_Intro", "duration": "30s"}
}

if __name__ == "__main__":
    run_pipeline(test_blueprint)