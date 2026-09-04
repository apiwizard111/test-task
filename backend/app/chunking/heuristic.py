import re
from pathlib import Path

from app.chunking.window import window_chunks
from app.models.chunk import CodeChunk

SIGNATURE = re.compile(
    r"^(?:"
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+(?P<js_fn>\w+)"
    r"|export\s+(?:default\s+)?class\s+(?P<js_class>\w+)"
    r"|(?:export\s+)?(?:async\s+)?function\s+(?P<js_fn2>\w+)"
    r"|(?:export\s+)?class\s+(?P<js_class2>\w+)"
    r"|func\s+(?:\([^)]*\)\s+)?(?P<go_fn>\w+)"
    r"|(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(?P<rs_fn>\w+)"
    r"|(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:class|interface)\s+(?P<java_type>\w+)"
    r")",
    re.MULTILINE,
)


def chunk_by_signature(path: Path, source: str, language: str) -> list[CodeChunk]:
    matches = list(SIGNATURE.finditer(source))
    if not matches:
        return window_chunks(path, source, language)

    lines = source.splitlines()
    starts = [_line_number(source, match.start()) for match in matches]
    names = [_match_name(match) for match in matches]
    chunks: list[CodeChunk] = []
    posix = path.as_posix()

    preamble_end = starts[0] - 1
    if preamble_end >= 1:
        preamble = "\n".join(lines[:preamble_end])
        if preamble.strip():
            chunks.append(
                CodeChunk(
                    id=f"{posix}:1-{preamble_end}:__module__",
                    path=posix,
                    language=language,
                    symbol="__module__",
                    start_line=1,
                    end_line=preamble_end,
                    text=preamble,
                )
            )

    for index, start in enumerate(starts):
        end = (starts[index + 1] - 1) if index + 1 < len(starts) else len(lines)
        text = "\n".join(lines[start - 1 : end])
        if not text.strip():
            continue
        symbol = names[index]
        chunks.append(
            CodeChunk(
                id=f"{posix}:{start}-{end}:{symbol}",
                path=posix,
                language=language,
                symbol=symbol,
                start_line=start,
                end_line=end,
                text=text,
            )
        )
    return chunks or window_chunks(path, source, language)


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _match_name(match: re.Match[str]) -> str:
    for value in match.groupdict().values():
        if value:
            return value
    return "block"
