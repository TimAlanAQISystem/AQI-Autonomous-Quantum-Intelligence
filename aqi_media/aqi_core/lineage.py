# aqi_core/lineage.py

class LineageTracker:
    def __init__(self):
        self.ledger = []

    def record_artifact(self, artifact_id, source_script, blueprint_ref, pipeline_version, parameters):
        entry = {
            "artifact_id": artifact_id,
            "source_script": source_script,
            "blueprint_ref": blueprint_ref,
            "pipeline_version": pipeline_version,
            "parameters": parameters,
            "timestamp": "simulated_timestamp"
        }
        self.ledger.append(entry)

    def get_lineage(self, artifact_id):
        return [entry for entry in self.ledger if entry["artifact_id"] == artifact_id]