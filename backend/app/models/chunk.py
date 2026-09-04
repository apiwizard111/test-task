from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CodeChunk:
    id: str
    path: str
    language: str
    symbol: str
    start_line: int
    end_line: int
    text: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> "CodeChunk":
        return cls(
            id=str(data["id"]),
            path=str(data["path"]),
            language=str(data["language"]),
            symbol=str(data["symbol"]),
            start_line=int(data["start_line"]),
            end_line=int(data["end_line"]),
            text=str(data["text"]),
        )

    def chroma_metadata(self) -> dict[str, str | int]:
        return {
            "path": self.path,
            "language": self.language,
            "symbol": self.symbol,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }
