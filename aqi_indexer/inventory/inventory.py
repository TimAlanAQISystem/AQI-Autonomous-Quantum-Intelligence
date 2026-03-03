"""Inventory module for AQI indexing system.

Provides a disciplined, non-destructive crawl of AQI_System_Root within
configured bounds and produces raw inventories of files, directories, and
integrity hashes. Output is deterministic, deterministic ordering and ready
for downstream metadata, graph, and auditing stages.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Iterator, Sequence


INVENTORY_DIRNAME = "aqi_inventory"
INVENTORY_JSON = "aqi_inventory.json"
INVENTORY_CSV = "aqi_inventory.csv"
HASH_BUFFER_SIZE = 1024 * 1024  # 1 MiB streaming chunks


@dataclass
class InventoryConfig:
    root: Path
    output_dir: Path
    max_depth: int = 10
    include_patterns: tuple[str, ...] = ("*",)
    exclude_patterns: tuple[str, ...] = ()
    hash_alg: str = "sha256"

    def inventory_dir(self) -> Path:
        return self.output_dir / INVENTORY_DIRNAME


@dataclass
class InventoryRecord:
    path: str
    relative_path: str
    size_bytes: int
    modified_ts: float
    hash_hex: str | None


class InventoryBuilder:
    """Crawls directory trees and yields inventory records."""

    def __init__(self, config: InventoryConfig) -> None:
        self.config = config
        self.root = config.root.resolve()

    def crawl(self) -> Iterator[InventoryRecord]:
        """Walk the root directory respecting depth and patterns."""
        for path in self._iter_paths(self.root, depth=0):
            stat = path.stat()
            rel_path = path.relative_to(self.root)
            hash_hex = self._compute_hash(path)
            yield InventoryRecord(
                path=str(path),
                relative_path=str(rel_path),
                size_bytes=stat.st_size,
                modified_ts=stat.st_mtime,
                hash_hex=hash_hex,
            )

    def _iter_paths(self, directory: Path, depth: int) -> Iterable[Path]:
        if depth > self.config.max_depth:
            return
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir():
                if self._is_excluded(entry):
                    continue
                yield from self._iter_paths(entry, depth + 1)
            elif entry.is_file() and self._is_included(entry):
                yield entry

    def _is_included(self, path: Path) -> bool:
        return _match_any(path.name, self.config.include_patterns) and not _match_any(
            path.name, self.config.exclude_patterns
        )

    def _is_excluded(self, path: Path) -> bool:
        return _match_any(path.name, self.config.exclude_patterns)

    def _compute_hash(self, path: Path) -> str | None:
        if not self.config.hash_alg:
            return None
        h = hashlib.new(self.config.hash_alg)
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(HASH_BUFFER_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()


def _match_any(name: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in patterns)


def run_inventory(config: InventoryConfig) -> list[InventoryRecord]:
    """Convenience wrapper that returns a list and writes artifacts."""
    builder = InventoryBuilder(config)
    records = list(builder.crawl())
    _write_inventory_outputs(config, records)
    return records


def _write_inventory_outputs(config: InventoryConfig, records: list[InventoryRecord]) -> None:
    inventory_dir = config.inventory_dir()
    inventory_dir.mkdir(parents=True, exist_ok=True)

    json_path = inventory_dir / INVENTORY_JSON
    csv_path = inventory_dir / INVENTORY_CSV

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump([asdict(record) for record in records], fh, indent=2)

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["path", "relative_path", "size_bytes", "modified_ts", "hash_hex"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
