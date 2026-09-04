import asyncio
import json
from pathlib import Path

from app.consts import REFUSAL_MESSAGE
from app.models.chunk import CodeChunk
from app.models.manifest import FileEntry, IngestManifest
from app.services.rag import RagService
from app.services.retrieve import RetrieveService
from app.services.store import Store
from tests.conftest import FakeLlm


def test_empty_retrieval_refuses_without_calling_llm(tmp_path: Path) -> None:
    asyncio.run(_empty_retrieval(tmp_path))


def test_citations_come_from_chunk_metadata(tmp_path: Path) -> None:
    asyncio.run(_citations(tmp_path))


async def _empty_retrieval(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.initialize()
    llm = FakeLlm(reply="SHOULD_NOT_RUN")
    rag = RagService(RetrieveService(store, llm), llm)
    events: list[tuple[str, dict]] = []
    async for raw in rag.stream_answer("How does auth work?", [], "req-1"):
        events.append(_parse_sse(raw))
    assert events[0][0] == "refusal"
    assert events[0][1]["text"] == REFUSAL_MESSAGE
    assert events[-1][0] == "done"
    assert events[-1][1]["refused"] is True
    assert events[-1][1]["citations"] == []


async def _citations(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.initialize()
    llm = FakeLlm(reply="Auth is in authenticate().")
    chunk = CodeChunk(
        id="app/auth.py:8-12:authenticate",
        path="app/auth.py",
        language="python",
        symbol="authenticate",
        start_line=8,
        end_line=12,
        text="def authenticate(key: str | None) -> str:\n    return key",
    )
    embeddings = await llm.embed([chunk.text])
    store.add_embeddings([chunk], embeddings)
    store.persist_corpus(
        [chunk],
        IngestManifest(
            name="fixture",
            source="sample",
            file_count=1,
            chunk_count=1,
            skipped_count=0,
            files=[FileEntry(path="app/auth.py", language="python", bytes=20, lines=2)],
        ),
    )
    rag = RagService(RetrieveService(store, llm), llm)
    events: list[tuple[str, dict]] = []
    async for raw in rag.stream_answer("How does authenticate work?", [], "req-2"):
        events.append(_parse_sse(raw))
    done = dict(events)["done"]
    assert done["refused"] is False
    assert done["citations"][0]["path"] == "app/auth.py"
    assert done["citations"][0]["start_line"] == 8
    assert "Auth is in authenticate" in "".join(
        payload["text"] for name, payload in events if name == "token"
    )


def _parse_sse(raw: str) -> tuple[str, dict]:
    event = "message"
    data = "{}"
    for line in raw.strip().split("\n"):
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        if line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
    return event, json.loads(data)
