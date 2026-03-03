"""
SuperIntelligence Module Scaffold
Purpose: Provide a safe, verifiable scaffold for an eventual 'superintelligence' attachable module.
This file DOES NOT include a model or heavy logic; it only provides a plugin interface with compatibility and safety checks.
"""
from dataclasses import dataclass
import json
import os
from typing import Optional


@dataclass
class ModuleMetadata:
    name: str
    version: str
    author: str
    description: str
    compat: dict


class SuperIntelligenceModule:
    def __init__(self, path: str):
        self.path = path
        self.loaded = False
        self.metadata: Optional[ModuleMetadata] = None

    def load_metadata(self):
        meta_path = os.path.join(self.path, 'module.json')
        if not os.path.exists(meta_path):
            raise FileNotFoundError('module.json not found in module path')
        with open(meta_path, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        self.metadata = ModuleMetadata(
            name=raw.get('name', 'unknown'),
            version=raw.get('version', '0.0.0'),
            author=raw.get('author', 'n/a'),
            description=raw.get('description', ''),
            compat=raw.get('compat', {}),
        )
        return self.metadata

    def is_compatible(self, platform_info: dict) -> bool:
        if not self.metadata:
            self.load_metadata()
        # Basic compat check: require minimal version fields
        required = self.metadata.compat or {}
        for k, v in required.items():
            if platform_info.get(k) != v:
                return False
        return True

    def connect(self, operator: str, platform_info: dict) -> bool:
        """Connect the module if compatible and operator is allowed.

        returns True if connected (loaded), otherwise raises an error.
        """
        # Safety gate: operator must be admin
        allowed_ops = ['founder', 'admin', 'operator']
        if operator not in allowed_ops:
            raise PermissionError('operator not permitted to attach superintelligence module')
        if not self.is_compatible(platform_info):
            raise RuntimeError('module not compatible with platform')
        # For now, mark as loaded and verify a signed manifest exists
        manifest_path = os.path.join(self.path, 'module_manifest.sig')
        if not os.path.exists(manifest_path):
            raise RuntimeError('missing module manifest; cannot ensure integrity')
        # NOTE: signature verification is expected to be implemented with GPG/HSM in production
        self.loaded = True
        return True

    def disconnect(self, operator: str):
        # Safety: only admins can disconnect
        allowed_ops = ['founder', 'admin']
        if operator not in allowed_ops:
            raise PermissionError('operator not permitted to disconnect')
        self.loaded = False
        return True

    def is_loaded(self):
        return self.loaded

    def __repr__(self):
        return f'<SuperIntelligenceModule path={self.path} loaded={self.loaded} metadata={self.metadata}>'
