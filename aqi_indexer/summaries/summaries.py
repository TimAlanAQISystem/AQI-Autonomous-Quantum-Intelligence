"""Summary generation for AQI indexing system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any


class SummaryGenerator:
    def __init__(self, inventory: List[dict], metadata: List[dict], crossrefs: dict, graph: dict):
        self.inventory = inventory
        self.metadata = metadata
        self.crossrefs = crossrefs
        self.graph = graph

        # Build lookup maps for efficient access
        self.metadata_by_path = {meta["relative_path"]: meta for meta in metadata}
        self.inventory_by_path = {item["relative_path"]: item for item in inventory}

    def summarize_file(self, file_entry: dict) -> dict:
        """
        Return a deterministic summary for a single file.
        """
        rel_path = file_entry["relative_path"]
        meta = self.metadata_by_path.get(rel_path, {})
        item = self.inventory_by_path.get(rel_path, {})

        # Get references from crossrefs
        forward_refs = self.crossrefs.get("forward_links", {}).get(rel_path, [])
        back_refs = self.crossrefs.get("backlinks", {}).get(rel_path, [])

        # Build deterministic summary text
        summary_parts = []

        # File type and size
        file_type = meta.get("file_type", "unknown")
        size_bytes = meta.get("size_bytes", 0)
        summary_parts.append(f"{file_type.upper()} file ({size_bytes} bytes)")

        # Tags
        tags = sorted(meta.get("tags", []))
        if tags:
            summary_parts.append(f"Tags: {', '.join(tags)}")

        # References
        if forward_refs:
            summary_parts.append(f"References {len(forward_refs)} files")
        if back_refs:
            summary_parts.append(f"Referenced by {len(back_refs)} files")

        summary = ". ".join(summary_parts) + "."

        return {
            "relative_path": rel_path,
            "file_type": file_type,
            "tags": tags,
            "size_bytes": size_bytes,
            "references": sorted(forward_refs),
            "referenced_by": sorted(back_refs),
            "summary": summary
        }

    def summarize_cluster(self, cluster_id: str, members: List[str]) -> dict:
        """
        Return a deterministic summary for a duplicate cluster.
        """
        # Sort members for determinism
        sorted_members = sorted(members)

        # Get common metadata from first member
        first_meta = self.metadata_by_path.get(sorted_members[0], {})
        file_type = first_meta.get("file_type", "unknown")

        summary = f"Duplicate cluster of {len(sorted_members)} {file_type} files with identical content."

        return {
            "cluster_id": cluster_id,
            "members": sorted_members,
            "summary": summary
        }

    def summarize_concepts(self, concepts: dict) -> dict:
        """
        Return deterministic summaries for concept stubs.
        concepts is {file_path: [concept_list]}
        """
        # Invert to {concept: [files]}
        concept_to_files = {}
        for file_path, concept_list in concepts.items():
            for concept in concept_list:
                if concept not in concept_to_files:
                    concept_to_files[concept] = []
                concept_to_files[concept].append(file_path)
        
        # Sort concepts and their files
        concept_summaries = {}
        for concept in sorted(concept_to_files.keys()):
            files = sorted(concept_to_files[concept])
            file_count = len(files)
            
            if file_count == 1:
                summary = f"Concept '{concept}' appears in 1 file."
            else:
                summary = f"Concept '{concept}' appears in {file_count} files."
            
            concept_summaries[concept] = {
                "files": files,
                "summary": summary
            }
        
        return concept_summaries

    def generate_all_summaries(self) -> dict:
        """
        Return all summaries.
        """
        # File summaries
        file_summaries = {}
        for item in self.inventory:
            summary = self.summarize_file(item)
            file_summaries[summary["relative_path"]] = summary

        # Cluster summaries (from duplicates)
        cluster_summaries = {}
        # Note: duplicates detection not implemented yet, so empty for now

        # Concept summaries
        concepts = self.crossrefs.get("concepts", {})
        concept_summaries = self.summarize_concepts(concepts)

        return {
            "file_summaries": file_summaries,
            "cluster_summaries": cluster_summaries,
            "concept_summaries": concept_summaries
        }


class SummaryWriter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir) / "aqi_summaries"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_file_summaries(self, file_summaries: dict) -> str:
        """Write aqi_summaries.json and return its path."""
        path = self.output_dir / "aqi_summaries.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(file_summaries, f, indent=2, sort_keys=True)
        return str(path)

    def write_cluster_summaries(self, cluster_summaries: dict) -> str:
        """Write aqi_cluster_summaries.json and return its path."""
        path = self.output_dir / "aqi_cluster_summaries.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(cluster_summaries, f, indent=2, sort_keys=True)
        return str(path)

    def write_concept_summaries(self, concept_summaries: dict) -> str:
        """Write aqi_concept_summaries.json and return its path."""
        path = self.output_dir / "aqi_concept_summaries.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(concept_summaries, f, indent=2, sort_keys=True)
        return str(path)


def run_summaries(
    inventory: List[dict],
    metadata: List[dict],
    crossrefs: dict,
    graph: dict,
    config
) -> dict:
    """
    Orchestrates summary generation and artifact writing.

    Returns:
    {
        "file_summaries_path": "...",
        "cluster_summaries_path": "...",
        "concept_summaries_path": "..."
    }
    """
    generator = SummaryGenerator(inventory, metadata, crossrefs, graph)
    writer = SummaryWriter(config.output_root)

    all_summaries = generator.generate_all_summaries()

    return {
        "file_summaries_path": writer.write_file_summaries(all_summaries["file_summaries"]),
        "cluster_summaries_path": writer.write_cluster_summaries(all_summaries["cluster_summaries"]),
        "concept_summaries_path": writer.write_concept_summaries(all_summaries["concept_summaries"])
    }
