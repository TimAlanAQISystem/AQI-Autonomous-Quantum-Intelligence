# pipeline/script_engine.py

class ScriptTimeline:
    def __init__(self, script: str):
        self.script = script

    def generate_timeline(self):
        # Split by paragraphs / logical beats
        lines = [line.strip() for line in self.script.split("\n") if line.strip()]
        timeline = []
        timestamp = 0.0

        for line in lines:
            segment = {
                "timestamp": timestamp,
                "text": line,
                "emphasis": False,
                "pause_after": 0.5
            }
            timeline.append(segment)
            # Increment timestamp with a rough estimate (e.g., 3s per line)
            timestamp += 3.0

        return timeline