import ast
from pathlib import Path

from app.chunking.window import window_chunks
from app.consts import MAX_SYMBOL_CHUNK_LINES
from app.models.chunk import CodeChunk


def chunk_python(path: Path, source: str) -> list[CodeChunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return window_chunks(path, source, "python")

    lines = source.splitlines()
    chunks: list[CodeChunk] = []
    first_def_line: int | None = None

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = _start_line(node)
        end = getattr(node, "end_lineno", None) or start
        if first_def_line is None:
            first_def_line = start
        chunks.extend(_bounded_slices(path, lines, start, end, node.name))
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    child_start = _start_line(child)
                    child_end = getattr(child, "end_lineno", None) or child_start
                    chunks.extend(
                        _bounded_slices(path, lines, child_start, child_end, f"{node.name}.{child.name}")
                    )

    if first_def_line and first_def_line > 1:
        preamble = "\n".join(lines[: first_def_line - 1])
        if preamble.strip():
            chunks.insert(0, _make_chunk(path, 1, first_def_line - 1, "__module__", preamble))

    filtered = [chunk for chunk in chunks if chunk.text.strip()]
    if not filtered:
        return window_chunks(path, source, "python")
    return filtered


def _start_line(node: ast.AST) -> int:
    start = int(getattr(node, "lineno"))
    decorators = getattr(node, "decorator_list", [])
    if decorators:
        return min(start, min(item.lineno for item in decorators))
    return start


def _bounded_slices(path: Path, lines: list[str], start: int, end: int, symbol: str) -> list[CodeChunk]:
    text = "\n".join(lines[start - 1 : end])
    if end - start + 1 > MAX_SYMBOL_CHUNK_LINES:
        return window_chunks(path, text, "python", line_offset=start - 1, symbol_prefix=symbol)
    return [_make_chunk(path, start, end, symbol, text)]


def _make_chunk(path: Path, start: int, end: int, symbol: str, text: str) -> CodeChunk:
    posix = path.as_posix()
    return CodeChunk(
        id=f"{posix}:{start}-{end}:{symbol}",
        path=posix,
        language="python",
        symbol=symbol,
        start_line=start,
        end_line=end,
        text=text,
    )
