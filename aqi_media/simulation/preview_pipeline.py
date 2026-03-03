# simulation/preview_pipeline.py

def generate_video_preview(simulation_results: dict) -> str:
    """
    Generates a human-readable preview of the video based on simulation results.
    This allows the steward to review the video content before any actual rendering or upload.
    """
    preview = []
    preview.append("=== AQI Video Preview ===")
    preview.append(f"Title: {simulation_results['output_spec']['metadata'].get('title', 'Untitled')}")
    preview.append(f"Duration: ~{len(simulation_results['timeline']) * 3} seconds (estimated)")
    preview.append(f"Format: {simulation_results['output_spec']['format']} at {simulation_results['output_spec']['resolution']}")
    preview.append("")

    preview.append("Voice Identity: " + simulation_results['voice_spec']['voice_identity'])
    preview.append(f"Pace: {simulation_results['voice_spec']['pace_wpm']} WPM")
    preview.append("")

    preview.append("Scene Breakdown:")
    for i, scene in enumerate(simulation_results['scene_specs']):
        preview.append(f"  Scene {i+1}: {scene['duration']}s - {scene.get('description', 'No description')}")
        preview.append(f"    Visual Style: {scene['style']}")
    preview.append("")

    preview.append("Audio Mix:")
    for track in simulation_results['mix_plan']['tracks']:
        preview.append(f"  {track['type']}: {track['gain_db']} dB")
    music_style = simulation_results['mix_plan']['music_profile'].get('style', 'default_cinematic')
    preview.append(f"  Music Style: {music_style}")
    preview.append("")

    preview.append("Timeline Summary:")
    for seg in simulation_results['timeline'][:5]:  # Show first 5 segments
        preview.append(f"  {seg['timestamp']}s: {seg['text'][:50]}...")
    if len(simulation_results['timeline']) > 5:
        preview.append(f"  ... and {len(simulation_results['timeline']) - 5} more segments")
    preview.append("")

    preview.append("Governance Status: " + ("BLOCKED (Steward approval required)" if simulation_results['publishing_blocked'] else "AUTHORIZED"))
    preview.append("")
    preview.append("This preview represents the planned video structure. Review and approve before proceeding to rendering.")

    return "\n".join(preview)