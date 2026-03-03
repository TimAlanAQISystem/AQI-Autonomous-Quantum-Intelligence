# test_tts.py

from pipeline.blueprint import MediaBlueprint
from pipeline.script_engine import ScriptTimeline
from pipeline.voice_spec import VoiceSpec
from integrations.tts_interface import TextToSpeechEngine
from aqi_core.governance import Governance

# Define the blueprint (same as before)
script = """
Introducing AQI Autonomous Quantum Intelligence.

This is the beginning of a new era...

[Full script would go here]
"""

storyboard = [
    {"duration": 60, "description": "Intro scene with fluid lattice"},
    {"duration": 180, "description": "Problem demonstration"},
    {"duration": 210, "description": "New category birth"},
    {"duration": 240, "description": "Necessity argument"},
    {"duration": 180, "description": "Architecture of trust"},
    {"duration": 210, "description": "World after AQI"},
    {"duration": 120, "description": "Why now"},
    {"duration": 60, "description": "Closing invitation"}
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
    gov = Governance()
    
    # For testing: Authorize publishing
    gov.authorize_publishing()
    print("Steward approval granted for testing.")
    
    # Check governance
    try:
        gov.assert_can_publish()
        print("Governance: Authorized")
    except PermissionError:
        print("Governance: BLOCKED - Cannot proceed to external tools")
        exit(1)
    
    # Generate voice spec
    timeline = ScriptTimeline(blueprint.script).generate_timeline()
    voice_spec = VoiceSpec("Confident Architect").build_spec(timeline)
    
    # Synthesize audio
    tts = TextToSpeechEngine()
    output_path = "aqi_intro_voiceover.wav"
    tts.synthesize(voice_spec, output_path)
    
    print(f"Voiceover generated: {output_path}")