"""Metadata extraction module for AQI indexing system."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from aqi_indexer.inventory.inventory import InventoryRecord


METADATA_DIRNAME = "aqi_metadata"
METADATA_JSON = "aqi_metadata.json"
EMBEDDINGS_NPY = "aqi_embeddings.npy"
DUPLICATES_JSON = "aqi_duplicates.json"
CLUSTERS_JSON = "aqi_clusters.json"


@dataclass
class MetadataConfig:
    output_dir: Path
    embedding_dimensions: int = 16
    enable_embeddings: bool = True
    enable_duplicates: bool = True

    def metadata_dir(self) -> Path:
        return self.output_dir / METADATA_DIRNAME


@dataclass
class FileMetadata:
    path: str
    relative_path: str
    file_type: str | None
    size_bytes: int
    modified_ts: float
    hash_hex: str | None
    tags: list[str]
    embedding: list[float] | None


class MetadataExtractor:
    """Derive deterministic metadata from inventory records."""

    def __init__(self, config: MetadataConfig) -> None:
        self.config = config

    def extract(self, records: Iterable[InventoryRecord]) -> list[FileMetadata]:
        metadata: list[FileMetadata] = []
        for record in records:
            file_type = self._classify(record)
            tags = self._tags(record, file_type)
            embedding = self._embedding(record) if self.config.enable_embeddings else None
            metadata.append(
                FileMetadata(
                    path=record.path,
                    relative_path=record.relative_path,
                    file_type=file_type,
                    size_bytes=record.size_bytes,
                    modified_ts=record.modified_ts,
                    hash_hex=record.hash_hex,
                    tags=tags,
                    embedding=embedding,
                )
            )
        return metadata

    def _classify(self, record: InventoryRecord) -> str | None:
        suffix = Path(record.path).suffix.lower()
        return suffix[1:] if suffix.startswith(".") else suffix or None

    def _tags(self, record: InventoryRecord, file_type: str | None) -> list[str]:
        tags: list[str] = []
        if file_type:
            tags.append(f"type:{file_type}")
        parts = Path(record.relative_path).parts
        if parts:
            tags.append(f"module:{parts[0]}")
        if "doc" in record.relative_path.lower():
            tags.append("hint:documentation")
        return sorted(set(tags))

    def _embedding(self, record: InventoryRecord) -> list[float]:
        dims = self.config.embedding_dimensions
        if dims <= 0:
            return []

        seed = record.relative_path.encode("utf-8")
        buffer = bytearray()
        counter = 0
        bytes_needed = dims * 2
        while len(buffer) < bytes_needed:
            buffer.extend(sha256(seed + counter.to_bytes(4, "big", signed=False)).digest())
            counter += 1

        return [int.from_bytes(buffer[i : i + 2], "big") / 65535 for i in range(0, bytes_needed, 2)]


def run_metadata(records: Sequence[InventoryRecord], config: MetadataConfig) -> list[FileMetadata]:
    extractor = MetadataExtractor(config)
    metadata = extractor.extract(records)
    _write_metadata_outputs(config, metadata)
    return metadata


def _write_metadata_outputs(config: MetadataConfig, metadata: list[FileMetadata]) -> None:
    metadata_dir = config.metadata_dir()
    metadata_dir.mkdir(parents=True, exist_ok=True)

    meta_path = metadata_dir / METADATA_JSON
    duplicates_path = metadata_dir / DUPLICATES_JSON
    clusters_path = metadata_dir / CLUSTERS_JSON
    embeddings_path = metadata_dir / EMBEDDINGS_NPY

    with meta_path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(item) for item in metadata], handle, indent=2)

    duplicates = _detect_duplicates(metadata) if config.enable_duplicates else {}
    with duplicates_path.open("w", encoding="utf-8") as handle:
        json.dump(duplicates, handle, indent=2)

    with clusters_path.open("w", encoding="utf-8") as handle:
        json.dump({"clusters": []}, handle, indent=2)

    embeddings = np.array([item.embedding or [] for item in metadata], dtype=float)
    np.save(embeddings_path, embeddings, allow_pickle=False)


def _detect_duplicates(metadata: Iterable[FileMetadata]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for item in metadata:
        if not item.hash_hex:
            continue
        buckets.setdefault(item.hash_hex, []).append(item.relative_path)
    return {hex_: sorted(paths) for hex_, paths in buckets.items() if len(paths) > 1}
