# pipeline/output_spec.py

class OutputSpecBuilder:
    def __init__(self, metadata):
        self.metadata = metadata

    def build_output_spec(self):
        return {
            "output_file": self.metadata.get("filename", "AQI_Intro_Final"),
            "format": self.metadata.get("format", "mp4"),
            "resolution": self.metadata.get("resolution", "1080p"),  # YouTube standard, can be 4K
            "codec": "H.264",  # YouTube recommended
            "frame_rate": 30,  # Standard for YouTube
            "aspect_ratio": "16:9",  # YouTube format
            "metadata": self.metadata
        }