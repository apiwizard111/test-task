from __future__ import annotations

import re
from collections.abc import Sequence

from app.models.manifest import IngestManifest

MENTION_RE = re.compile(r"@([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)")
TEST_WORD_RE = re.compile(r"\b(test|tests|pytest|unittest|спек|тест)\b", flags=re.IGNORECASE)
MAX_ATTACHED_PATHS = 20


def extract_mentions(text: str) -> list[str]:
    return list(dict.fromkeys(MENTION_RE.findall(text)))


def mentions_tests(question: str) -> bool:
    return bool(TEST_WORD_RE.search(question))


def resolve_attached_paths(requested: Sequence[str], manifest: IngestManifest | None) -> list[str]:
    if manifest is None or not requested:
        return []
    known = {entry.path: entry.path for entry in manifest.files}
    known_lower = {entry.path.lower(): entry.path for entry in manifest.files}
    resolved: list[str] = []
    for raw in requested:
        cleaned = raw.strip().lstrip("@").replace("\\", "/")
        if not cleaned:
            continue
        path = _resolve_one(cleaned, known, known_lower, manifest)
        if path is None or path in resolved:
            continue
        resolved.append(path)
        if len(resolved) >= MAX_ATTACHED_PATHS:
            break
    return resolved


def _resolve_one(
    cleaned: str,
    known: dict[str, str],
    known_lower: dict[str, str],
    manifest: IngestManifest,
) -> str | None:
    if cleaned in known:
        return known[cleaned]
    lowered = cleaned.lower()
    if lowered in known_lower:
        return known_lower[lowered]
    matches = [
        entry.path
        for entry in manifest.files
        if entry.path.endswith("/" + cleaned) or entry.path == cleaned
    ]
    if len(matches) == 1:
        return matches[0]
    return None
