from app.models.manifest import FileEntry, IngestManifest
from app.services.mentions import extract_mentions, resolve_attached_paths


def test_extract_mentions_from_message() -> None:
    assert extract_mentions("Explain @sync/local.py and @storage/base.py please") == [
        "sync/local.py",
        "storage/base.py",
    ]


def test_resolve_attached_paths_exact_and_basename() -> None:
    manifest = IngestManifest(
        name="demo",
        source="zip",
        file_count=2,
        chunk_count=2,
        skipped_count=0,
        files=[
            FileEntry(path="sync/local.py", language="python", bytes=10, lines=20),
            FileEntry(path="storage/base.py", language="python", bytes=10, lines=20),
        ],
    )
    assert resolve_attached_paths(["@sync/local.py", "base.py"], manifest) == [
        "sync/local.py",
        "storage/base.py",
    ]
