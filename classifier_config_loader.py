"""
ClassifierConfigLoader — YAML Config with Hot-Reload
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Loads classifier_config.yaml and auto-reloads when the file changes.
This lets you tune thresholds between campaigns without restarting.

Usage:
    loader = ClassifierConfigLoader()
    config = loader.get()         # Returns config dict, reloads if file changed
    classifier = CallTypeClassifier(config)

Author: Claude Opus 4.6 — AQI System Expert
Date: February 18, 2026
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import yaml — fallback to JSON-style config if yaml not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("[CONFIG] PyYAML not installed — will use built-in defaults. "
                   "Install with: pip install pyyaml")


class ClassifierConfigLoader:
    """
    Load and hot-reload classifier configuration from YAML.
    
    Features:
      - Auto-detects file changes via mtime (no polling thread needed)
      - Falls back to built-in defaults if YAML is unavailable
      - Thread-safe (reads are atomic dict assignments)
    """

    DEFAULT_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "classifier_config.yaml"
    )

    def __init__(self, path: str = None, auto_reload: bool = True):
        """
        Args:
            path: Path to YAML config file. Defaults to ./classifier_config.yaml
            auto_reload: If True, checks mtime on every get() call
        """
        self.path = path or self.DEFAULT_PATH
        self.auto_reload = auto_reload
        self._last_mtime: float = 0
        self._config: Optional[Dict[str, Any]] = None
        self._load()

    def _load(self):
        """Load config from YAML file."""
        if not YAML_AVAILABLE:
            logger.info("[CONFIG] Using built-in defaults (PyYAML not available)")
            self._config = None
            return

        if not os.path.exists(self.path):
            logger.warning(f"[CONFIG] Config file not found: {self.path} — using defaults")
            self._config = None
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            self._last_mtime = os.path.getmtime(self.path)
            logger.info(f"[CONFIG] Loaded classifier config from {self.path}")
        except Exception as e:
            logger.error(f"[CONFIG] Failed to load {self.path}: {e} — using defaults")
            self._config = None

    def get(self) -> Optional[Dict[str, Any]]:
        """
        Get current config, reloading from disk if file has changed.
        
        Returns:
            Config dict (or None if using defaults)
        """
        if self.auto_reload and YAML_AVAILABLE and os.path.exists(self.path):
            try:
                current_mtime = os.path.getmtime(self.path)
                if current_mtime != self._last_mtime:
                    logger.info(f"[CONFIG] Config file changed — reloading")
                    self._load()
            except Exception:
                pass  # Non-critical — use cached config

        return self._config

    def get_or_default(self, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get config or return provided default if YAML is unavailable."""
        config = self.get()
        return config if config is not None else default_config
