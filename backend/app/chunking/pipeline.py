from pathlib import Path

from app.chunking.heuristic import chunk_by_signature
from app.chunking.python_ast import chunk_python
from app.chunking.window import window_chunks
from app.consts import HEURISTIC_LANGUAGES, language_for
from app.models.chunk import CodeChunk


def chunk_source(path: Path, source: str) -> list[CodeChunk]:
    language = language_for(path)
    if language == "python":
        return chunk_python(path, source)
    if language in HEURISTIC_LANGUAGES:
        return chunk_by_signature(path, source, language)
    return window_chunks(path, source, language)
