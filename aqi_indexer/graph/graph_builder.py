"""Knowledge graph builder for AQI indexing system."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aqi_indexer.crossrefs.crossrefs import CrossReference
from aqi_indexer.metadata.metadata import FileMetadata


@dataclass
class GraphConfig:
    output_dir: Path


class KnowledgeGraphBuilder:
    def __init__(self, config: GraphConfig) -> None:
        self.config = config

    def build(self, metadata: Iterable[FileMetadata], crossrefs: Iterable[CrossReference]) -> str:
        """Build and write the knowledge graph as JSON artifacts."""
        # Build nodes from metadata
        nodes = []
        for meta in metadata:
            nodes.append({
                "file_path": str(meta.relative_path),
                "file_type": meta.file_type,
                "size_bytes": meta.size_bytes,
                "modified_time": meta.modified_ts,
                "hash_sha256": meta.hash_hex,
                "tags": sorted(meta.tags) if meta.tags else [],
                "embedding": meta.embedding
            })
        
        # Sort nodes deterministically
        nodes.sort(key=lambda x: x["file_path"])

        # Build edges from crossrefs
        edges = []
        for xref in crossrefs:
            edges.append({
                "source_path": str(xref.source),
                "target_path": str(xref.target),
                "edge_type": xref.relation,
                "score": xref.score
            })
        
        # Sort edges deterministically
        edges.sort(key=lambda x: (x["source_path"], x["target_path"], x["edge_type"]))

        # Write artifacts
        output_dir = self.config.output_dir / "aqi_graph"
        output_dir.mkdir(parents=True, exist_ok=True)

        import json
        
        # Write nodes
        nodes_path = output_dir / "aqi_graph_nodes.json"
        with nodes_path.open("w", encoding="utf-8") as f:
            json.dump(nodes, f, indent=2)
        
        # Write edges
        edges_path = output_dir / "aqi_graph_edges.json"
        with edges_path.open("w", encoding="utf-8") as f:
            json.dump(edges, f, indent=2)

        return str(output_dir)
