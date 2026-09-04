from pathlib import Path

from app.consts import (
    ALLOWED_EXTENSIONS,
    IGNORE_DIR_NAMES,
    IGNORE_FILE_NAMES,
    MAX_FILE_BYTES,
)


def should_skip_dir(name: str) -> bool:
    return name.lower() in IGNORE_DIR_NAMES or name.startswith(".")


def should_skip_file(path: Path, size: int) -> bool:
    if path.name.lower() in IGNORE_FILE_NAMES:
        return True
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return True
    if size > MAX_FILE_BYTES:
        return True
    return False
