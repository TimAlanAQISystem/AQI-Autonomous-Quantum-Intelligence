"""Cross-reference detection for AQI indexing system."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from aqi_indexer.metadata.metadata import FileMetadata
from typing import List, Dict, Any

class CrossReferenceExtractor:
    def __init__(self, inventory: List[dict], metadata: List[dict]):
        """Initialize with inventory and metadata records."""
        self.inventory = inventory
        self.metadata = metadata
        self.relative_paths = {item.relative_path for item in inventory}

    def extract_markdown_links(self, text: str) -> List[str]:
        """Return sorted list of relative paths referenced via Markdown links."""
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, text)
        paths = [match[1] for match in matches if match[1] in self.relative_paths]
        return sorted(set(paths))

    def extract_python_imports(self, text: str) -> List[str]:
        """Return sorted list of module paths referenced via Python imports."""
        import_pattern = r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        from_pattern = r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
        matches = re.findall(import_pattern, text, re.MULTILINE) + re.findall(from_pattern, text, re.MULTILINE)
        paths = [match.replace('.', '/') + '.py' for match in matches if match.replace('.', '/') + '.py' in self.relative_paths]
        return sorted(set(paths))

    def extract_inline_file_mentions(self, text: str) -> List[str]:
        """Return sorted list of filenames mentioned in plain text."""
        pattern = r'\b([a-zA-Z0-9_]+\.[a-zA-Z0-9]+)\b'
        matches = re.findall(pattern, text)
        paths = [match for match in matches if match in self.relative_paths]
        return sorted(set(paths))

    def extract_concepts_stub(self, text: str) -> List[str]:
        """Return deterministic placeholder concepts (stub)."""
        return ["concept:stub"]

    def extract_all_references(self, file_path: str) -> Dict[str, List[str]]:
        """
        Return:
        {
            "markdown_links": [...],
            "python_imports": [...],
            "inline_mentions": [...],
            "concepts": [...]
        }
        """
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            text = ""
        return {
            "markdown_links": self.extract_markdown_links(text),
            "python_imports": self.extract_python_imports(text),
            "inline_mentions": self.extract_inline_file_mentions(text),
            "concepts": self.extract_concepts_stub(text)
        }

class CrossReferenceGraph:
    def __init__(self, inventory: List[dict], metadata: List[dict], extractor: CrossReferenceExtractor):
        """Initialize with inventory, metadata, and extractor."""
        self.inventory = inventory
        self.metadata = metadata
        self.extractor = extractor
        self.relative_paths = {item.relative_path for item in inventory}

    def build_forward_links(self) -> Dict[str, List[str]]:
        """Return mapping: relative_path → sorted list of referenced paths."""
        forward_links = {}
        for item in self.inventory:
            rel_path = item.relative_path
            full_path = item.path
            refs = self.extractor.extract_all_references(full_path)
            all_refs = refs['markdown_links'] + refs['python_imports'] + refs['inline_mentions']
            if all_refs:
                forward_links[rel_path] = sorted(set(all_refs))
        return forward_links

    def build_backlinks(self, forward_links: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Return mapping: relative_path → sorted list of files that reference it."""
        backlinks = {}
        for source, targets in forward_links.items():
            for target in targets:
                if target not in backlinks:
                    backlinks[target] = []
                backlinks[target].append(source)
        for target in backlinks:
            backlinks[target] = sorted(set(backlinks[target]))
        return backlinks

    def build_graph_structure(self, forward_links: Dict[str, List[str]], backlinks: Dict[str, List[str]]) -> Dict[str, Any]:
        """Return a deterministic graph structure for visualization or analysis."""
        nodes = sorted(set(forward_links.keys()) | set(backlinks.keys()))
        edges = []
        for source, targets in forward_links.items():
            for target in targets:
                edges.append({"source": source, "target": target, "relation": "references"})
        edges.sort(key=lambda x: (x['source'], x['target']))
        return {"nodes": nodes, "edges": edges}

    def validate_links(self, forward_links: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Return only valid links (filter out references to non-existent files)."""
        valid_links = {}
        for source, targets in forward_links.items():
            valid_targets = [t for t in targets if t in self.relative_paths]
            if valid_targets:
                valid_links[source] = sorted(set(valid_targets))
        return valid_links

class CrossReferenceWriter:
    def __init__(self, output_dir: str):
        """Initialize with output directory."""
        self.output_dir = Path(output_dir) / "aqi_crossrefs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_crossrefs_json(self, forward_links: Dict[str, List[str]]) -> str:
        """Write aqi_crossrefs.json and return its path."""
        path = self.output_dir / "aqi_crossrefs.json"
        with path.open("w", encoding="utf-8") as f:
            import json
            json.dump(forward_links, f, indent=2)
        return str(path)

    def write_backlinks_json(self, backlinks: Dict[str, List[str]]) -> str:
        """Write aqi_backlinks.json and return its path."""
        path = self.output_dir / "aqi_backlinks.json"
        with path.open("w", encoding="utf-8") as f:
            import json
            json.dump(backlinks, f, indent=2)
        return str(path)

    def write_concepts_json(self, concepts: Dict[str, List[str]]) -> str:
        """Write aqi_concepts.json (stub) and return its path."""
        path = self.output_dir / "aqi_concepts.json"
        with path.open("w", encoding="utf-8") as f:
            import json
            json.dump(concepts, f, indent=2)
        return str(path)

    def write_graph_json(self, graph: Dict[str, Any]) -> str:
        """Write aqi_link_graph.json and return its path."""
        path = self.output_dir / "aqi_link_graph.json"
        with path.open("w", encoding="utf-8") as f:
            import json
            json.dump(graph, f, indent=2)
        return str(path)

def run_crossrefs(inventory: List[dict], metadata: List[dict], config: Any) -> Dict[str, str]:
    """
    Orchestrates:
    - extraction
    - forward links
    - backlinks
    - concept stubs
    - graph structure
    - artifact writing

    Returns:
    {
        "crossrefs_path": "...",
        "backlinks_path": "...",
        "concepts_path": "...",
        "graph_path": "..."
    }
    """
    extractor = CrossReferenceExtractor(inventory, metadata)
    graph_builder = CrossReferenceGraph(inventory, metadata, extractor)
    writer = CrossReferenceWriter(config.output_root)

    forward_links = graph_builder.build_forward_links()
    validated_links = graph_builder.validate_links(forward_links)
    backlinks = graph_builder.build_backlinks(validated_links)
    graph = graph_builder.build_graph_structure(validated_links, backlinks)

    # Stub concepts
    concepts = {item.relative_path: ["concept:stub"] for item in inventory}

    return {
        "crossrefs_path": writer.write_crossrefs_json(validated_links),
        "backlinks_path": writer.write_backlinks_json(backlinks),
        "concepts_path": writer.write_concepts_json(concepts),
        "graph_path": writer.write_graph_json(graph)
    }

@dataclass
class CrossrefConfig:
    enable_similarity_links: bool = True
    similarity_threshold: float = 0.8


@dataclass
class CrossReference:
    source: Path
    target: Path
    relation: str
    score: float | None = None


class CrossReferenceBuilder:
    def __init__(self, config: CrossrefConfig) -> None:
        self.config = config

    def build(self, metadata: Iterable[FileMetadata]) -> list[CrossReference]:
        """Derive cross references from metadata."""
        raise NotImplementedError

    def _scan_relations(self, meta: FileMetadata) -> list[CrossReference]:
        raise NotImplementedError
