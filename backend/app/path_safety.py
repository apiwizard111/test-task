from __future__ import annotations

from pathlib import Path


def resolve_under(root: Path, relative_path: str) -> Path:
    """Resolve *relative_path* under *root* or raise FileNotFoundError (path escape)."""
    base = root.resolve()
    cleaned = relative_path.replace("\\", "/").lstrip("/")
    target = (base / cleaned).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise FileNotFoundError(relative_path) from exc
    return target
