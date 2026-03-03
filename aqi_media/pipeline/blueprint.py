# pipeline/blueprint.py

class MediaBlueprint:
    def __init__(self, script, storyboard, visual_style, audio_style, metadata, governance_id):
        self.script = script
        self.storyboard = storyboard
        self.visual_style = visual_style
        self.audio_style = audio_style
        self.metadata = metadata
        self.governance_id = governance_id

    def validate(self):
        # Verify essential fields exist and are non-empty
        # This is simulation-level validation, not execution.
        if not self.script:
            raise ValueError("Script is required.")
        if not isinstance(self.storyboard, list) or not self.storyboard:
            raise ValueError("Storyboard must be a non-empty list.")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary.")
        return True