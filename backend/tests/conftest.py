from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

SAMPLE_REPO = Path(__file__).resolve().parents[2] / "sample_repo"


class FakeLlm:
    def __init__(self, reply: str = "Authentication uses the X-API-Key header in app/auth.py.") -> None:
        self.reply = reply

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(text) for text in texts]

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield self.reply


def _hash_vector(text: str, dim: int = 32) -> list[float]:
    vector = [0.0] * dim
    for token in text.lower().replace("/", " ").replace("_", " ").split():
        vector[hash(token) % dim] += 1.0
    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        return vector
    return [value / norm for value in vector]


@pytest.fixture
def fake_llm() -> FakeLlm:
    return FakeLlm()


@pytest.fixture
def client(tmp_path: Path, fake_llm: FakeLlm) -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        sample_repo_dir=SAMPLE_REPO,
        openai_api_key="test-key",
        debug_retrieval=True,
    )
    app = create_app(settings=settings, llm=fake_llm)
    with TestClient(app) as test_client:
        yield test_client
