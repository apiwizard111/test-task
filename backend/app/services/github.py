from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass

import httpx

from app.consts import MAX_ZIP_BYTES

GITHUB_RE = re.compile(
    r"(?:https?://github\.com/)?(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
    r"(?:/(?:tree|blob)/(?P<branch>[^/\s]+))?",
    re.IGNORECASE,
)
DEFAULT_BRANCHES = ("main", "master")
ZIPBALL_URL = "https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"


class GithubIngestError(ValueError):
    pass


@dataclass(slots=True)
class GithubRepo:
    owner: str
    repo: str
    branch: str | None


def parse_github_url(url: str) -> GithubRepo:
    match = GITHUB_RE.search(url.strip())
    if match is None:
        raise GithubIngestError("Not a GitHub repository URL")
    repo = match.group("repo").removesuffix(".git")
    return GithubRepo(owner=match.group("owner"), repo=repo, branch=match.group("branch"))


async def download_zipball(url: str) -> bytes:
    parsed = parse_github_url(url)
    branches = [parsed.branch] if parsed.branch else list(DEFAULT_BRANCHES)
    last_error = "Repository not found"
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=60.0,
        headers={"User-Agent": "RepoLens/0.1"},
    ) as client:
        try:
            for branch in branches:
                if branch is None:
                    continue
                zip_url = ZIPBALL_URL.format(owner=parsed.owner, repo=parsed.repo, branch=branch)
                response = await client.get(zip_url)
                if response.status_code == 404:
                    last_error = f"Branch {branch} not found"
                    continue
                if response.status_code >= 400:
                    raise GithubIngestError(f"GitHub returned HTTP {response.status_code}")
                if len(response.content) > MAX_ZIP_BYTES:
                    raise GithubIngestError("Repository zip exceeds the 20MB demo limit")
                _assert_zip(response.content)
                return response.content
        except httpx.HTTPError as exc:
            raise GithubIngestError("Could not download the GitHub repository") from exc
    raise GithubIngestError(last_error)


def _assert_zip(payload: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if archive.testzip() is not None:
                raise GithubIngestError("Corrupt zip from GitHub")
    except zipfile.BadZipFile as exc:
        raise GithubIngestError("GitHub response was not a zip archive") from exc
