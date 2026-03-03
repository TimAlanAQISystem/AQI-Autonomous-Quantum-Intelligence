# campaign_autopilot_config_loader.py

import yaml

def load_autopilot_config(path: str = "campaign_autopilot_config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)
