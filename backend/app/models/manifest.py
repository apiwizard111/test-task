from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FileEntry:
    path: str
    language: str
    bytes: int
    lines: int


@dataclass(slots=True)
class IngestManifest:
    name: str
    source: str
    file_count: int
    chunk_count: int
    skipped_count: int
    files: list[FileEntry]

    def to_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "file_count": self.file_count,
            "chunk_count": self.chunk_count,
            "skipped_count": self.skipped_count,
            "files": [
                {
                    "path": item.path,
                    "language": item.language,
                    "bytes": item.bytes,
                    "lines": item.lines,
                }
                for item in self.files
            ],
        }

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> "IngestManifest":
        files = [
            FileEntry(
                path=str(item["path"]),
                language=str(item["language"]),
                bytes=int(item["bytes"]),
                lines=int(item["lines"]),
            )
            for item in data.get("files", [])
        ]
        return cls(
            name=str(data["name"]),
            source=str(data["source"]),
            file_count=int(data["file_count"]),
            chunk_count=int(data["chunk_count"]),
            skipped_count=int(data["skipped_count"]),
            files=files,
        )
