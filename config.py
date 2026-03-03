# config.py

from dataclasses import dataclass
import os

@dataclass
class N8NConfig:
    base_url: str
    api_key: str

    @classmethod
    def from_env(cls) -> "N8NConfig":
        return cls(
            base_url=os.environ.get("N8N_BASE_URL", "https://your-n8n-url"),
            api_key=os.environ.get("N8N_API_KEY", "REPLACE_ME"),
        )