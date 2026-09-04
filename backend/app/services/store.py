from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.consts import CHROMA_DIRNAME, CHUNKS_FILENAME, COLLECTION_NAME, MANIFEST_FILENAME, SOURCES_DIRNAME
from app.models.chunk import CodeChunk
from app.models.manifest import IngestManifest
from app.observability import log_event
from app.path_safety import resolve_under

logger = logging.getLogger("store")


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.chroma_dir = data_dir / CHROMA_DIRNAME
        self.sources_dir = data_dir / SOURCES_DIRNAME
        self.chunks_path = data_dir / CHUNKS_FILENAME
        self.manifest_path = data_dir / MANIFEST_FILENAME
        self._client: Any = None
        self._collection: Any = None
        self.chunks: list[CodeChunk] = []
        self.manifest: IngestManifest | None = None
        self.generation = 0

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.chunks = self._load_chunks()
        self.manifest = self._load_manifest()
        log_event(
            logger,
            "store_loaded",
            chunk_count=len(self.chunks),
            ingested=self.manifest is not None,
        )

    @property
    def collection(self) -> Any:
        if self._collection is None:
            raise RuntimeError("Store is not initialized")
        return self._collection

    @property
    def is_ready(self) -> bool:
        return self.manifest is not None and len(self.chunks) > 0

    def reset(self) -> None:
        if self._client is not None:
            names = set(self._client.list_collections())
            if COLLECTION_NAME in names:
                self._client.delete_collection(COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        if self.sources_dir.exists():
            shutil.rmtree(self.sources_dir)
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.chunks = []
        self.manifest = None
        self.generation += 1
        if self.chunks_path.exists():
            self.chunks_path.unlink()
        if self.manifest_path.exists():
            self.manifest_path.unlink()

    def persist_corpus(self, chunks: list[CodeChunk], manifest: IngestManifest) -> None:
        self.chunks = chunks
        self.manifest = manifest
        self.generation += 1
        self.chunks_path.write_text(
            json.dumps([chunk.to_record() for chunk in chunks], indent=2),
            encoding="utf-8",
        )
        self.manifest_path.write_text(json.dumps(manifest.to_record(), indent=2), encoding="utf-8")

    def add_embeddings(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        if not chunks:
            return
        self.collection.add(
            ids=[chunk.id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.chroma_metadata() for chunk in chunks],
        )

    def query_vectors(self, embedding: list[float], k: int) -> list[tuple[CodeChunk, float]]:
        if not self.chunks or self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(k, len(self.chunks)),
            include=["metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        by_id = {chunk.id: chunk for chunk in self.chunks}
        ranked: list[tuple[CodeChunk, float]] = []
        for chunk_id, distance in zip(ids, distances, strict=False):
            chunk = by_id.get(chunk_id)
            if chunk is None:
                continue
            score = 1.0 - float(distance)
            ranked.append((chunk, score))
        return ranked

    def read_source(self, relative_path: str) -> str:
        target = resolve_under(self.sources_dir, relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return target.read_text(encoding="utf-8", errors="replace")

    def _load_chunks(self) -> list[CodeChunk]:
        if not self.chunks_path.exists():
            return []
        raw = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        return [CodeChunk.from_record(item) for item in raw]

    def _load_manifest(self) -> IngestManifest | None:
        if not self.manifest_path.exists():
            return None
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return IngestManifest.from_record(raw)
