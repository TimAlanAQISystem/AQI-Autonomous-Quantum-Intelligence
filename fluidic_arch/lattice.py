# lattice.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LatticeNode:
    node_id: str
    label: str
    coherence_weight: float


@dataclass
class LatticeEdge:
    source: str
    target: str
    strength: float


@dataclass
class LatticeRegion:
    name: str
    node_ids: List[str]


@dataclass
class Lattice:
    nodes: Dict[str, LatticeNode]
    edges: List[LatticeEdge]
    regions: List[LatticeRegion]

    def coherence_score(self) -> float:
        score = 0.0
        for edge in self.edges:
            src = self.nodes[edge.source]
            tgt = self.nodes[edge.target]
            score += edge.strength * (src.coherence_weight + tgt.coherence_weight) / 2.0
        return score