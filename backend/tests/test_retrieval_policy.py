from app.models.chunk import CodeChunk
from app.models.manifest import FileEntry, IngestManifest
from app.services.mentions import mentions_tests
from app.services.rag import build_file_index
from app.services.retrieve import RankedChunk, diversify_by_path, is_overview_query, is_test_path


def test_overview_query_detection() -> None:
    assert is_overview_query("Огляд файлів у проекті")
    assert is_overview_query("List all files in the repository")
    assert is_overview_query("What is the project structure?")
    assert not is_overview_query("How does LocalSyncBackend upload keys?")


def test_diversify_prefers_non_test_paths() -> None:
    ranked = [
        _ranked("tests/test_sync.py", "test_upload", 0.9),
        _ranked("tests/test_styled_html.py", "test_import", 0.8),
        _ranked("sync/local.py", "LocalSyncBackend", 0.7),
        _ranked("storage/base.py", "Repository", 0.6),
        _ranked("gui.py", "App", 0.5),
    ]
    chosen = diversify_by_path(ranked, limit=3, max_per_path=1, prefer_non_test=True)
    paths = [item.chunk.path for item in chosen]
    assert paths == ["sync/local.py", "storage/base.py", "gui.py"]


def test_file_index_lists_every_path() -> None:
    index = build_file_index(
        IngestManifest(
            name="demo",
            source="zip",
            file_count=2,
            chunk_count=2,
            skipped_count=0,
            files=[
                FileEntry(path="sync/local.py", language="python", bytes=10, lines=20),
                FileEntry(path="tests/test_sync.py", language="python", bytes=10, lines=40),
            ],
        )
    )
    assert "<file_index>" in index
    assert "sync/local.py" in index
    assert "tests/test_sync.py" in index


def test_test_path_helper() -> None:
    assert is_test_path("tests/test_sync.py")
    assert is_test_path("pkg/test_foo.py")
    assert not is_test_path("sync/local.py")
    assert mentions_tests("explain the pytest suite")
    assert not mentions_tests("how does storage work")


def _ranked(path: str, symbol: str, score: float) -> RankedChunk:
    return RankedChunk(
        chunk=CodeChunk(
            id=f"{path}:{symbol}",
            path=path,
            language="python",
            symbol=symbol,
            start_line=1,
            end_line=2,
            text="pass",
        ),
        score=score,
    )
