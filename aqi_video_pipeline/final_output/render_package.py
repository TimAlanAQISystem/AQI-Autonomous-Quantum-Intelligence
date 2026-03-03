class RenderPackage:
    def package(self, scenes, audio, metadata):
        # Simulate final packaging
        print("📦 Packaging final video")
        # Mock processing time
        import time
        time.sleep(0.03)
        title = metadata.get("title", "AQI_Video")
        print(f"✅ Video packaged: {title}_Final.mp4")
        return f"{title}_Final.mp4"