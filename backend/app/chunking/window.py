from pathlib import Path

from app.consts import WINDOW_LINES, WINDOW_OVERLAP_LINES
from app.models.chunk import CodeChunk


def window_chunks(
    path: Path,
    source: str,
    language: str,
    line_offset: int = 0,
    symbol_prefix: str = "",
) -> list[CodeChunk]:
    lines = source.splitlines()
    if not lines:
        return []

    posix = path.as_posix()
    chunks: list[CodeChunk] = []
    start = 0
    step = max(WINDOW_LINES - WINDOW_OVERLAP_LINES, 1)
    part = 0

    while start < len(lines):
        end = min(start + WINDOW_LINES, len(lines))
        text = "\n".join(lines[start:end])
        if text.strip():
            start_line = line_offset + start + 1
            end_line = line_offset + end
            symbol = symbol_prefix or f"{posix}#{part}"
            if symbol_prefix and part:
                symbol = f"{symbol_prefix}#{part}"
            chunks.append(
                CodeChunk(
                    id=f"{posix}:{start_line}-{end_line}:{symbol}",
                    path=posix,
                    language=language,
                    symbol=symbol,
                    start_line=start_line,
                    end_line=end_line,
                    text=text,
                )
            )
            part += 1
        if end == len(lines):
            break
        start += step
    return chunks
