class TimelineSynchronizer:
    def sync(self, scenes, audio):
        # Simulate timeline sync
        print("⏰ Synchronizing timeline")
        timeline = []
        for i, scene in enumerate(scenes):
            timeline.append({
                "timestamp": i * 5.0,
                "scene_id": scene.split('_')[1].split('.')[0],  # Extract id from filename
                "audio_segment": i
            })
        print("✅ Timeline synchronized")
        return {"timeline": timeline}