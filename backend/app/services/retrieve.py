from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.consts import BM25_K, FINAL_K, RRF_K, VECTOR_K
from app.models.chunk import CodeChunk
from app.models.manifest import IngestManifest
from app.services.llm import LlmGateway
from app.services.store import Store

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
CAMEL = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)")
OVERVIEW_RE = re.compile(
    r"(?:"
    r"\b(?:overview|structure|architecture|inventory|modules?|packages?|directories|folders?)\b|"
    r"\b(?:all|every|entire|whole)\b.{0,40}\b(?:files?|codebase|repo(?:sitory)?|project|modules?)\b|"
    r"\b(?:list|show|map)\b.{0,40}\b(?:files?|tree|modules?|packages?)\b|"
    r"(?:огляд|структур\w*|архітектур\w*|усі\s+файл\w*|всі\s+файл\w*|які\s+файл\w*|"
    r"список\s+файл\w*|карта\s+проект\w*|що\s+є\s+в\s+проект\w*)"
    r")",
    flags=re.IGNORECASE,
)
TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|testing|__tests__|spec)(?:/|$)|(?:^|/)test_[^/]+$|[^/]+_test\.py$",
    flags=re.IGNORECASE,
)


@dataclass(slots=True)
class RankedChunk:
    chunk: CodeChunk
    score: float


class RetrieveService:
    def __init__(self, store: Store, llm: LlmGateway) -> None:
        self._store = store
        self._llm = llm
        self._bm25: BM25Okapi | None = None
        self._fingerprint = -1

    @property
    def manifest(self) -> IngestManifest | None:
        return self._store.manifest

    async def retrieve(self, query: str) -> list[RankedChunk]:
        if not self._store.chunks:
            return []
        self._refresh_bm25()
        query_embedding = (await self._llm.embed([query]))[0]
        vector_hits = await asyncio.to_thread(self._store.query_vectors, query_embedding, VECTOR_K)
        bm25_hits = await asyncio.to_thread(self._bm25_hits, query, BM25_K)
        fused = reciprocal_rank_fusion(
            [[chunk for chunk, _ in vector_hits], [chunk for chunk, _ in bm25_hits]],
            k=RRF_K,
        )
        return fused[: max(FINAL_K * 3, 18)]

    def corpus_sample(self) -> list[RankedChunk]:
        """Deterministic path-diverse sample for overview prompts (no similarity)."""
        ranked = [
            RankedChunk(chunk=chunk, score=1.0 / (index + 1))
            for index, chunk in enumerate(self._store.chunks)
        ]
        return diversify_by_path(ranked, limit=24, max_per_path=1, prefer_non_test=True)

    def chunks_for_paths(self, paths: Sequence[str], *, per_path: int = 6) -> list[RankedChunk]:
        if not paths:
            return []
        wanted = set(paths)
        by_path: dict[str, list[CodeChunk]] = {path: [] for path in paths}
        for chunk in self._store.chunks:
            if chunk.path not in wanted:
                continue
            bucket = by_path[chunk.path]
            if len(bucket) >= per_path:
                continue
            bucket.append(chunk)
        pinned: list[RankedChunk] = []
        score = 1000.0
        for path in paths:
            for chunk in sorted(by_path.get(path, []), key=lambda item: item.start_line):
                pinned.append(RankedChunk(chunk=chunk, score=score))
                score -= 1.0
        return pinned

    def _refresh_bm25(self) -> None:
        fingerprint = self._store.generation
        if self._bm25 is not None and fingerprint == self._fingerprint:
            return
        corpus = [tokenize(bm25_document(chunk)) for chunk in self._store.chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._fingerprint = fingerprint

    def _bm25_hits(self, query: str, k: int) -> list[tuple[CodeChunk, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:k]
        hits: list[tuple[CodeChunk, float]] = []
        for index, score in ranked:
            if score <= 0:
                continue
            hits.append((self._store.chunks[index], float(score)))
        return hits


def reciprocal_rank_fusion(ranked_lists: list[list[CodeChunk]], k: int = RRF_K) -> list[RankedChunk]:
    scores: dict[str, float] = {}
    by_id: dict[str, CodeChunk] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            by_id[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [RankedChunk(chunk=by_id[chunk_id], score=score) for chunk_id, score in ordered]


def diversify_by_path(
    ranked: list[RankedChunk],
    *,
    limit: int,
    max_per_path: int = 2,
    prefer_non_test: bool = False,
) -> list[RankedChunk]:
    if prefer_non_test:
        candidates = [item for item in ranked if not is_test_path(item.chunk.path)] + [
            item for item in ranked if is_test_path(item.chunk.path)
        ]
    else:
        candidates = ranked

    selected: list[RankedChunk] = []
    per_path: dict[str, int] = {}
    per_top: dict[str, int] = {}
    max_per_top = 3 if prefer_non_test else 4

    for item in candidates:
        path = item.chunk.path
        top = path.split("/", 1)[0]
        if per_path.get(path, 0) >= max_per_path:
            continue
        if per_top.get(top, 0) >= max_per_top:
            continue
        selected.append(item)
        per_path[path] = per_path.get(path, 0) + 1
        per_top[top] = per_top.get(top, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def is_overview_query(question: str) -> bool:
    return bool(OVERVIEW_RE.search(question))


def is_test_path(path: str) -> bool:
    return bool(TEST_PATH_RE.search(path.replace("\\", "/")))


def bm25_document(chunk: CodeChunk) -> str:
    return f"{chunk.path} {chunk.symbol} {chunk.text}"


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in IDENTIFIER.finditer(text):
        raw = match.group(0)
        lowered = raw.lower()
        tokens.append(lowered)
        if "_" in raw:
            tokens.extend(part.lower() for part in raw.split("_") if part)
        else:
            parts = CAMEL.findall(raw)
            if len(parts) > 1:
                tokens.extend(part.lower() for part in parts)
    return tokens
