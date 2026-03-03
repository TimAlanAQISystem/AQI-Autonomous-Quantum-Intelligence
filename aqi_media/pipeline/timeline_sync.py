# pipeline/timeline_sync.py

class TimelineSynchronizer:
    def build_master_timeline(self, scene_specs, voice_spec):
        # Simplified mapping for simulation: sequential scenes
        master = []
        current_time = 0.0
        for spec in scene_specs:
            master.append({
                "scene_id": spec["scene_id"],
                "start_time": current_time,
                "end_time": current_time + spec["duration"]
            })
            current_time += spec["duration"]

        return {
            "scenes": master,
            "voice": voice_spec
        }