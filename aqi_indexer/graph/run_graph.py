"""Graph building runner for AQI indexing system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from aqi_indexer.crossrefs.crossrefs import CrossReference
from aqi_indexer.graph.graph_builder import GraphConfig, KnowledgeGraphBuilder
from aqi_indexer.metadata.metadata import FileMetadata


def run_graph(
    metadata: Iterable[FileMetadata],
    crossrefs_paths: dict,
    output_root: Path
) -> str:
    """
    Build the knowledge graph from metadata and cross-references.

    crossrefs_paths should contain the paths returned by run_crossrefs.
    Returns the path to the output directory.
    """
    # Read crossrefs from artifacts
    crossrefs_file = Path(crossrefs_paths["crossrefs_path"])
    with crossrefs_file.open("r", encoding="utf-8") as f:
        forward_links = json.load(f)

    # Convert to CrossReference objects
    crossrefs = []
    for source, targets in forward_links.items():
        source_path = Path(source)
        for target in targets:
            crossrefs.append(CrossReference(
                source=source_path,
                target=Path(target),
                relation="references",
                score=None
            ))

    config = GraphConfig(output_dir=output_root)
    builder = KnowledgeGraphBuilder(config)
    output_dir = builder.build(metadata, crossrefs)

    return output_dir