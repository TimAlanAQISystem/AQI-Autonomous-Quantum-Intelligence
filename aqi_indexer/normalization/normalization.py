"""Normalization module for AQI indexing system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any


class NormalizationRules:
    def __init__(self, config):
        self.config = config

    def normalize_tag(self, tag: str) -> str:
        """
        Return canonical tag form (lowercased, trimmed, mapped).
        """
        # Basic normalization: lowercase and strip
        normalized = tag.lower().strip()

        # Apply canonical mappings (fixed rules)
        tag_mappings = {
            "type:py": "code/python",
            "type:pyc": "code/python-compiled",
            "type:md": "doc/markdown",
            "type:json": "data/json",
            "type:npy": "data/numpy",
            "type:csv": "data/csv",
            "module:__init__.py": "module/init",
            "module:__pycache__": "module/cache",
            "hint:documentation": "doc/hint"
        }

        return tag_mappings.get(normalized, normalized)

    def normalize_file_type(self, file_type: str, path: str) -> str:
        """
        Map raw file_type/extension to canonical category.
        """
        if not file_type:
            return "unknown"

        # File type mappings
        type_mappings = {
            "py": "code/python",
            "pyc": "code/python-compiled",
            "md": "doc/markdown",
            "json": "data/json",
            "npy": "data/numpy",
            "csv": "data/csv",
            "txt": "doc/text",
            "yml": "config/yaml",
            "yaml": "config/yaml",
            "toml": "config/toml",
            "ini": "config/ini"
        }

        return type_mappings.get(file_type.lower(), f"other/{file_type.lower()}")

    def normalize_concept_name(self, concept: str) -> str:
        """
        Return canonical concept name (namespaced, lowercased, stable).
        """
        if not concept:
            return "concept/unknown"

        # Basic normalization
        normalized = concept.lower().strip()

        # Apply concept mappings
        concept_mappings = {
            "concept:stub": "concept/stub"
        }

        return concept_mappings.get(normalized, normalized)

    def build_rule_index(self) -> dict:
        """
        Return a dictionary describing the normalization rules used.
        """
        return {
            "tag_rules": {
                "lowercase": True,
                "strip_whitespace": True,
                "canonical_mappings": {
                    "type:py": "code/python",
                    "type:pyc": "code/python-compiled",
                    "type:md": "doc/markdown",
                    "type:json": "data/json",
                    "type:npy": "data/numpy",
                    "type:csv": "data/csv",
                    "module:__init__.py": "module/init",
                    "module:__pycache__": "module/cache",
                    "hint:documentation": "doc/hint"
                }
            },
            "file_type_rules": {
                "mappings": {
                    "py": "code/python",
                    "pyc": "code/python-compiled",
                    "md": "doc/markdown",
                    "json": "data/json",
                    "npy": "data/numpy",
                    "csv": "data/csv",
                    "txt": "doc/text",
                    "yml": "config/yaml",
                    "yaml": "config/yaml",
                    "toml": "config/toml",
                    "ini": "config/ini"
                },
                "default_pattern": "other/{extension}"
            },
            "concept_rules": {
                "lowercase": True,
                "strip_whitespace": True,
                "canonical_mappings": {
                    "concept:stub": "concept/stub"
                }
            }
        }


class NormalizationEngine:
    def __init__(self, inventory, metadata, crossrefs, graph, summaries, rules):
        self.inventory = inventory
        self.metadata = metadata
        self.crossrefs = crossrefs
        self.graph = graph
        self.summaries = summaries
        self.rules = rules

    def normalize_metadata(self) -> list[dict]:
        """
        Return new metadata list with normalized file_type and tags.
        """
        normalized_metadata = []

        for meta in self.metadata:
            normalized_meta = dict(meta)  # Copy the dict

            # Normalize file_type
            original_type = meta.get("file_type", "")
            normalized_meta["file_type"] = self.rules.normalize_file_type(
                original_type, meta.get("relative_path", "")
            )

            # Normalize tags
            original_tags = meta.get("tags", [])
            normalized_meta["tags"] = sorted([
                self.rules.normalize_tag(tag) for tag in original_tags
            ])

            normalized_metadata.append(normalized_meta)

        # Sort by relative_path for determinism
        normalized_metadata.sort(key=lambda x: x.get("relative_path", ""))

        return normalized_metadata

    def normalize_crossrefs(self) -> dict:
        """
        Return crossrefs mapping with normalized concepts.
        """
        normalized_crossrefs = dict(self.crossrefs)  # Copy

        # Normalize concepts
        if "concepts" in normalized_crossrefs:
            normalized_concepts = {}
            for file_path, concepts in normalized_crossrefs["concepts"].items():
                normalized_concepts[file_path] = sorted([
                    self.rules.normalize_concept_name(concept) for concept in concepts
                ])
            normalized_crossrefs["concepts"] = normalized_concepts

        return normalized_crossrefs

    def normalize_graph_nodes(self) -> dict:
        """
        Return updated graph nodes structure with normalized fields.
        """
        normalized_graph = dict(self.graph)  # Copy

        if "nodes" in normalized_graph:
            normalized_nodes = []
            for node in normalized_graph["nodes"]:
                normalized_node = dict(node)

                # Normalize file_type if present
                if "file_type" in normalized_node:
                    normalized_node["file_type"] = self.rules.normalize_file_type(
                        normalized_node["file_type"], normalized_node.get("file_path", "")
                    )

                # Normalize tags if present
                if "tags" in normalized_node:
                    normalized_node["tags"] = sorted([
                        self.rules.normalize_tag(tag) for tag in normalized_node["tags"]
                    ])

                normalized_nodes.append(normalized_node)

            # Sort nodes by file_path for determinism
            normalized_nodes.sort(key=lambda x: x.get("file_path", ""))
            normalized_graph["nodes"] = normalized_nodes

        return normalized_graph

    def normalize_summaries(self) -> dict:
        """
        Return updated summaries with normalized tags and concept names.
        """
        normalized_summaries = dict(self.summaries)  # Copy

        # Normalize file summaries
        if "file_summaries" in normalized_summaries:
            normalized_file_summaries = {}
            for file_path, summary in normalized_summaries["file_summaries"].items():
                normalized_summary = dict(summary)

                # Normalize tags
                if "tags" in normalized_summary:
                    normalized_summary["tags"] = sorted([
                        self.rules.normalize_tag(tag) for tag in normalized_summary["tags"]
                    ])

                normalized_file_summaries[file_path] = normalized_summary

            normalized_summaries["file_summaries"] = normalized_file_summaries

        # Normalize concept summaries
        if "concept_summaries" in normalized_summaries:
            normalized_concept_summaries = {}
            for concept_name, concept_data in normalized_summaries["concept_summaries"].items():
                normalized_concept_name = self.rules.normalize_concept_name(concept_name)
                normalized_concept_summaries[normalized_concept_name] = concept_data

            normalized_summaries["concept_summaries"] = normalized_concept_summaries

        return normalized_summaries

    def build_normalized_views(self) -> dict:
        """
        Return a composite normalized view.
        """
        return {
            "metadata": self.normalize_metadata(),
            "crossrefs": self.normalize_crossrefs(),
            "graph": self.normalize_graph_nodes(),
            "summaries": self.normalize_summaries()
        }


class NormalizationWriter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir) / "aqi_normalization"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_normalized_metadata(self, normalized_metadata: list[dict]) -> str:
        """Write aqi_metadata_normalized.json and return its path."""
        path = self.output_dir / "aqi_metadata_normalized.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(normalized_metadata, f, indent=2, sort_keys=True)
        return str(path)

    def write_normalized_graph(self, normalized_graph: dict) -> str:
        """Write aqi_graph_normalized.json and return its path."""
        path = self.output_dir / "aqi_graph_normalized.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(normalized_graph, f, indent=2, sort_keys=True)
        return str(path)

    def write_normalized_summaries(self, normalized_summaries: dict) -> str:
        """Write aqi_summaries_normalized.json and return its path."""
        path = self.output_dir / "aqi_summaries_normalized.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(normalized_summaries, f, indent=2, sort_keys=True)
        return str(path)

    def write_normalization_index(self, rule_index: dict) -> str:
        """Write aqi_normalization_index.json and return its path."""
        path = self.output_dir / "aqi_normalization_index.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(rule_index, f, indent=2, sort_keys=True)
        return str(path)


def run_normalization(
    inventory: List[dict],
    metadata: List[dict],
    crossrefs: dict,
    graph: dict,
    summaries: dict,
    config
) -> dict:
    """
    Orchestrates normalization and artifact writing.

    Returns:
    {
        "normalized_metadata_path": "...",
        "normalized_graph_path": "...",
        "normalized_summaries_path": "...",
        "normalization_index_path": "..."
    }
    """
    rules = NormalizationRules(config)
    engine = NormalizationEngine(inventory, metadata, crossrefs, graph, summaries, rules)
    writer = NormalizationWriter(config.output_root)

    normalized_views = engine.build_normalized_views()
    rule_index = rules.build_rule_index()

    return {
        "normalized_metadata_path": writer.write_normalized_metadata(normalized_views["metadata"]),
        "normalized_graph_path": writer.write_normalized_graph(normalized_views["graph"]),
        "normalized_summaries_path": writer.write_normalized_summaries(normalized_views["summaries"]),
        "normalization_index_path": writer.write_normalization_index(rule_index)
    }
