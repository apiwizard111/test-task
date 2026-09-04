from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Sequence

from openai import APIError

from app.consts import MAX_CONTEXT_CHARS, MAX_HISTORY_MESSAGES, REFUSAL_MESSAGE, SYSTEM_PROMPT
from app.models.chat import ChatTurn, Citation, RetrievedChunk
from app.models.manifest import IngestManifest
from app.observability import log_event
from app.services.llm import LlmGateway, llm_error_detail
from app.services.mentions import extract_mentions, mentions_tests, resolve_attached_paths
from app.services.retrieve import RankedChunk, RetrieveService, diversify_by_path, is_overview_query

logger = logging.getLogger("rag")

MAX_PINNED_CHUNKS_PER_FILE = 6


class RagService:
    def __init__(self, retriever: RetrieveService, llm: LlmGateway, debug: bool = False) -> None:
        self._retriever = retriever
        self._llm = llm
        self._debug = debug

    async def stream_answer(
        self,
        question: str,
        history: list[ChatTurn],
        request_id: str,
        paths: Sequence[str] | None = None,
    ) -> AsyncIterator[str]:
        started = time.perf_counter()
        overview = is_overview_query(question)
        file_index = build_file_index(self._retriever.manifest)
        pinned_paths = resolve_attached_paths(
            [*(paths or ()), *extract_mentions(question)],
            self._retriever.manifest,
        )
        pinned = self._retriever.chunks_for_paths(pinned_paths, per_path=MAX_PINNED_CHUNKS_PER_FILE)
        ranked = await self._rank(question, overview=overview, has_pins=bool(pinned_paths))
        merged = merge_pinned(pinned, ranked)

        if not merged and not file_index:
            yield _sse("refusal", {"text": REFUSAL_MESSAGE})
            yield _sse("done", {"citations": [], "retrieved": [], "refused": True})
            log_event(logger, "rag_refused", request_id=request_id, reason="empty_retrieval")
            return

        context, used = build_context(merged, file_index=file_index)
        messages = build_messages(question, history, context)
        yield _sse(
            "meta",
            {
                "retrieved": [item.model_dump() for item in retrieved_payload(used)],
                "pinned": pinned_paths,
            },
        )

        try:
            async for token in self._llm.stream_chat(messages):
                yield _sse("token", {"text": token})
        except APIError as exc:
            detail = llm_error_detail(exc)
            yield _sse("error", {"text": detail})
            log_event(logger, "rag_llm_failed", request_id=request_id, error=detail)
            return

        citations = [
            Citation(
                path=item.chunk.path,
                symbol=item.chunk.symbol,
                start_line=item.chunk.start_line,
                end_line=item.chunk.end_line,
            )
            for item in used
        ]
        yield _sse(
            "done",
            {
                "citations": [item.model_dump() for item in citations],
                "retrieved": [item.model_dump() for item in retrieved_payload(used)] if self._debug else [],
                "refused": False,
            },
        )
        log_event(
            logger,
            "rag_complete",
            request_id=request_id,
            duration_ms=int((time.perf_counter() - started) * 1000),
            retrieved=len(used),
            overview=overview,
            pinned=pinned_paths,
            top_paths=[item.chunk.path for item in used[:3]],
            top_score=round(used[0].score, 4) if used else 0,
        )

    async def _rank(
        self,
        question: str,
        *,
        overview: bool,
        has_pins: bool,
    ) -> list[RankedChunk]:
        if overview and not has_pins:
            return diversify_by_path(
                self._retriever.corpus_sample(),
                limit=12,
                max_per_path=1,
                prefer_non_test=True,
            )
        return diversify_by_path(
            await self._retriever.retrieve(question),
            limit=6,
            max_per_path=2,
            prefer_non_test=not mentions_tests(question),
        )


def merge_pinned(pinned: list[RankedChunk], ranked: list[RankedChunk]) -> list[RankedChunk]:
    seen: set[str] = set()
    merged: list[RankedChunk] = []
    for item in [*pinned, *ranked]:
        if item.chunk.id in seen:
            continue
        seen.add(item.chunk.id)
        merged.append(item)
    return merged


def build_file_index(manifest: IngestManifest | None) -> str:
    if manifest is None or not manifest.files:
        return ""
    lines = [
        f"{entry.path}\t{entry.language}\t{entry.lines} lines"
        for entry in sorted(manifest.files, key=lambda item: item.path.lower())
    ]
    return "<file_index>\n" + "\n".join(lines) + "\n</file_index>"


def build_context(ranked: list[RankedChunk], *, file_index: str) -> tuple[str, list[RankedChunk]]:
    parts: list[str] = []
    used: list[RankedChunk] = []
    total = 0
    if file_index:
        parts.append(file_index)
        total += len(file_index)

    for item in ranked:
        excerpt = (
            f'<excerpt path="{item.chunk.path}" symbol="{item.chunk.symbol}" '
            f'lines="{item.chunk.start_line}-{item.chunk.end_line}">\n'
            f"{item.chunk.text}\n"
            "</excerpt>"
        )
        if total + len(excerpt) > MAX_CONTEXT_CHARS and used:
            break
        if total + len(excerpt) > MAX_CONTEXT_CHARS and not used and not file_index:
            break
        if total + len(excerpt) > MAX_CONTEXT_CHARS and not used:
            continue
        parts.append(excerpt)
        used.append(item)
        total += len(excerpt)
    return "\n\n".join(parts), used


def build_messages(question: str, history: list[ChatTurn], context: str) -> list[dict[str, str]]:
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in trimmed:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(
        {
            "role": "user",
            "content": f"<context>\n{context}\n</context>\n\nQuestion: {question}",
        }
    )
    return messages


def retrieved_payload(ranked: list[RankedChunk]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            path=item.chunk.path,
            symbol=item.chunk.symbol,
            start_line=item.chunk.start_line,
            end_line=item.chunk.end_line,
            score=round(item.score, 4),
        )
        for item in ranked
    ]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
