from __future__ import annotations

import asyncio
import io
import logging
import shutil
import zipfile
from pathlib import Path

from app.chunking.filters import should_skip_dir, should_skip_file
from app.chunking.pipeline import chunk_source
from app.consts import MAX_CHUNKS, MAX_FILES, MAX_ZIP_BYTES, language_for
from app.models.chunk import CodeChunk
from app.models.manifest import FileEntry, IngestManifest
from app.observability import log_event
from app.services.github import download_zipball
from app.services.llm import LlmGateway
from app.services.store import Store

logger = logging.getLogger("ingest")

SAMPLE_SOURCE = "sample"
GITHUB_SOURCE = "github"
ZIP_SOURCE = "zip"


class IngestError(ValueError):
    pass


class IngestService:
    def __init__(self, store: Store, llm: LlmGateway, sample_repo_dir: Path) -> None:
        self._store = store
        self._llm = llm
        self._sample_repo_dir = sample_repo_dir

    async def ingest_sample(self) -> IngestManifest:
        if not self._sample_repo_dir.is_dir():
            raise IngestError("Sample repository is not available")
        return await self._ingest_directory(self._sample_repo_dir, "nexus-tasks", SAMPLE_SOURCE)

    async def ingest_github(self, url: str) -> IngestManifest:
        payload = await download_zipball(url)
        return await self.ingest_zip_bytes(payload, name=_repo_name(url), source=GITHUB_SOURCE)

    async def ingest_zip_bytes(self, payload: bytes, name: str, source: str = ZIP_SOURCE) -> IngestManifest:
        if len(payload) > MAX_ZIP_BYTES:
            raise IngestError("Zip exceeds the 20MB demo limit")
        scratch = self._store.data_dir / "_unpack"
        if scratch.exists():
            shutil.rmtree(scratch)
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(_extract_zip, payload, scratch)
            root = _unwrap_single_root(scratch)
            return await self._ingest_directory(root, name, source)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    async def _ingest_directory(self, root: Path, name: str, source: str) -> IngestManifest:
        files, skipped = await asyncio.to_thread(_collect_files, root)
        if not files:
            raise IngestError("No supported source files found")

        await asyncio.to_thread(self._store.reset)
        copied, entries = await asyncio.to_thread(_copy_sources, files, root, self._store.sources_dir)
        chunks = await asyncio.to_thread(_chunk_copied_files, copied, entries)
        if not chunks:
            raise IngestError("No chunks produced from the repository")

        embeddings = await self._llm.embed([chunk.text for chunk in chunks])
        await asyncio.to_thread(self._store.add_embeddings, chunks, embeddings)
        manifest = IngestManifest(
            name=name,
            source=source,
            file_count=len(entries),
            chunk_count=len(chunks),
            skipped_count=skipped,
            files=entries,
        )
        await asyncio.to_thread(self._store.persist_corpus, chunks, manifest)
        log_event(
            logger,
            "ingest_complete",
            name=name,
            source=source,
            file_count=manifest.file_count,
            chunk_count=manifest.chunk_count,
            skipped_count=skipped,
        )
        return manifest


def _collect_files(root: Path) -> tuple[list[Path], int]:
    selected: list[Path] = []
    skipped = 0
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(should_skip_dir(part) for part in path.relative_to(root).parts[:-1]):
            skipped += 1
            continue
        size = path.stat().st_size
        if should_skip_file(path, size):
            skipped += 1
            continue
        selected.append(path)
        if len(selected) > MAX_FILES:
            raise IngestError(f"Repository exceeds the {MAX_FILES} file demo limit")
    return selected, skipped


def _copy_sources(files: list[Path], root: Path, dest: Path) -> tuple[list[Path], list[FileEntry]]:
    copied: list[Path] = []
    entries: list[FileEntry] = []
    for path in files:
        relative = path.relative_to(root)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        text = target.read_text(encoding="utf-8", errors="replace")
        copied.append(target)
        entries.append(
            FileEntry(
                path=relative.as_posix(),
                language=language_for(path),
                bytes=target.stat().st_size,
                lines=len(text.splitlines()),
            )
        )
    return copied, entries


def _chunk_copied_files(files: list[Path], entries: list[FileEntry]) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for path, entry in zip(files, entries, strict=True):
        source = path.read_text(encoding="utf-8", errors="replace")
        for chunk in chunk_source(Path(entry.path), source):
            chunks.append(chunk)
            if len(chunks) > MAX_CHUNKS:
                raise IngestError(f"Repository exceeds the {MAX_CHUNKS} chunk demo limit")
    return chunks


def _extract_zip(payload: bytes, dest: Path) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            _safe_extract(archive, dest)
    except zipfile.BadZipFile as exc:
        raise IngestError("Upload is not a valid zip archive") from exc


def _safe_extract(archive: zipfile.ZipFile, dest: Path) -> None:
    dest_root = dest.resolve()
    for info in archive.infolist():
        target = (dest / info.filename).resolve()
        try:
            target.relative_to(dest_root)
        except ValueError as exc:
            raise IngestError("Zip contains an unsafe path") from exc
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out)


def _unwrap_single_root(scratch: Path) -> Path:
    children = [path for path in scratch.iterdir() if path.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return scratch


def _repo_name(url: str) -> str:
    cleaned = url.rstrip("/").removesuffix(".git")
    return cleaned.split("/")[-1] or "repository"
