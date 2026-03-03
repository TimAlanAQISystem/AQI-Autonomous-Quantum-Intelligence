# simulation/simulate_pipeline.py

from aqi_core.governance import Governance
from pipeline.blueprint import MediaBlueprint
from pipeline.script_engine import ScriptTimeline
from pipeline.voice_spec import VoiceSpec
from pipeline.visual_composer import VisualComposer
from pipeline.render_planner import RenderPlanner
from pipeline.timeline_sync import TimelineSynchronizer
from pipeline.audio_spec import AudioMixSpec
from pipeline.output_spec import OutputSpecBuilder

def simulate_intro_video(blueprint: MediaBlueprint):
    gov = Governance()

    # 1. Validate blueprint
    blueprint.validate()

    # 2. Script timeline
    timeline = ScriptTimeline(blueprint.script).generate_timeline()

    # 3. Voice spec
    voice_spec = VoiceSpec("Confident Architect").build_spec(timeline)

    # 4. Visual composition
    scene_specs = VisualComposer(blueprint.storyboard, blueprint.visual_style).build_scene_specs()

    # 5. Render planning
    render_plan = RenderPlanner().build_render_plan(scene_specs)

    # 6. Timeline sync
    master_timeline = TimelineSynchronizer().build_master_timeline(scene_specs, voice_spec)

    # 7. Audio mix plan
    mix_plan = AudioMixSpec(blueprint.audio_style).build_mix_plan(voice_spec)

    # 8. Output spec
    output_spec = OutputSpecBuilder(blueprint.metadata).build_output_spec()

    # 9. Governance check (this will block publishing)
    try:
        gov.assert_can_publish()
    except PermissionError as e:
        blocked = True
    else:
        blocked = False

    return {
        "timeline": timeline,
        "voice_spec": voice_spec,
        "scene_specs": scene_specs,
        "render_plan": render_plan,
        "master_timeline": master_timeline,
        "mix_plan": mix_plan,
        "output_spec": output_spec,
        "publishing_blocked": blocked
    }