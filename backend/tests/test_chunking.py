from pathlib import Path

from app.chunking.python_ast import chunk_python
from app.chunking.window import window_chunks


SOURCE = '''\
"""Nexus auth helpers."""

API_KEY_HEADER = "X-API-Key"

class AuthError(Exception):
    pass

def authenticate(key: str | None) -> str:
    if not key:
        raise AuthError("missing")
    return key

class TaskService:
    def list_visible(self) -> list[str]:
        return []

    def assign(self, actor: str) -> None:
        if actor != "admin":
            raise AuthError("nope")
'''


def test_python_chunker_splits_functions_and_methods() -> None:
    chunks = chunk_python(Path("app/auth.py"), SOURCE)
    symbols = {chunk.symbol for chunk in chunks}
    assert "authenticate" in symbols
    assert "TaskService" in symbols
    assert "TaskService.list_visible" in symbols
    assert "TaskService.assign" in symbols
    assert "__module__" in symbols
    auth = next(chunk for chunk in chunks if chunk.symbol == "authenticate")
    assert "def authenticate" in auth.text
    assert auth.start_line < auth.end_line
    assert auth.path == "app/auth.py"


def test_python_syntax_error_falls_back_to_windows() -> None:
    chunks = chunk_python(Path("broken.py"), "def nope(\n")
    assert chunks
    assert chunks[0].language == "python"


def test_window_chunks_do_not_cross_implied_file_end() -> None:
    lines = "\n".join(f"line-{index}" for index in range(1, 50))
    chunks = window_chunks(Path("notes.md"), lines, "markdown")
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 49
    assert all(chunk.path == "notes.md" for chunk in chunks)
