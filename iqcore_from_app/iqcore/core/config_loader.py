import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config')

def load_rules(filename: str) -> dict:
    with open(os.path.join(CONFIG_PATH, filename), 'r') as f:
        return yaml.safe_load(f)

def load_flags(filename: str) -> dict:
    with open(os.path.join(CONFIG_PATH, filename), 'r') as f:
        return yaml.safe_load(f)

def load_thresholds(filename: str) -> dict:
    with open(os.path.join(CONFIG_PATH, filename), 'r') as f:
        return yaml.safe_load(f)