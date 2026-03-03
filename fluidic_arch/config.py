# config.py

from enum import Enum, auto


class Environment(Enum):
    DEV = auto()
    PROD = auto()


# Global config knobs
MAX_ACTIVE_DMAS_BASE = 16
MAX_PATTERNS_PER_CONTAINER = 32
DMA_MAX_LIFETIME_SEC = 30.0

DEFAULT_ENVIRONMENT = Environment.DEV