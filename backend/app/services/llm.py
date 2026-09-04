from __future__ import annotations

import hashlib
import math
import re
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from openai import APIError, AsyncOpenAI

from app.consts import EMBED_BATCH_SIZE
from app.settings import Settings

GROQ_CHAT_MODEL = "openai/gpt-oss-20b"
LOCAL_EMBED_MODEL = "local"
OPENAI_CHAT_DEFAULTS = frozenset({"gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini"})
DEPRECATED_GROQ_CHAT = frozenset(
    {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
        "gemma-7b-it",
        "gemma2-9b-it",
    }
)
GROQ_CHAT_PREFERENCE = (
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)
GROQ_SKIP_TOKENS = ("whisper", "tts", "orpheus", "prompt-guard", "llama-guard", "guard", "embed")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
LOCAL_EMBED_DIM = 256


class LlmGateway(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


class OpenAiGateway:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        chat_model, embed_model = resolve_models(settings)
        self._is_groq = "groq.com" in (settings.openai_base_url or "").lower()
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        self._embed_model = embed_model
        self._chat_model = chat_model
        self._chat_resolved = not self._is_groq
        self._local_embedder = LocalTokenEmbedder() if embed_model == LOCAL_EMBED_MODEL else None

    @property
    def chat_model(self) -> str:
        return self._chat_model

    @property
    def embedding_model(self) -> str:
        return self._embed_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._local_embedder is not None:
            return self._local_embedder.embed(texts)
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            response = await self._client.embeddings.create(model=self._embed_model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([item.embedding for item in ordered])
        return vectors

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        await self._resolve_groq_chat_model()
        stream = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            temperature=0.1,
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta

    async def _resolve_groq_chat_model(self) -> None:
        if self._chat_resolved:
            return
        listed = await self._client.models.list()
        available = [item.id for item in listed.data]
        self._chat_model = pick_groq_chat_model(available, self._chat_model)
        self._chat_resolved = True


class LocalTokenEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hashed_vector(text) for text in texts]


def resolve_models(settings: Settings) -> tuple[str, str]:
    chat = settings.llm_model
    embed = settings.embedding_model
    if uses_local_embeddings(settings):
        if chat in OPENAI_CHAT_DEFAULTS or chat in DEPRECATED_GROQ_CHAT:
            chat = GROQ_CHAT_MODEL
        return chat, LOCAL_EMBED_MODEL
    return chat, embed


def uses_local_embeddings(settings: Settings) -> bool:
    host = (settings.openai_base_url or "").lower()
    if "groq.com" in host:
        return True
    return settings.embedding_model.strip().lower() in {LOCAL_EMBED_MODEL, "hash"}


def pick_groq_chat_model(available: Sequence[str], requested: str) -> str:
    ids = list(available)
    if requested in ids:
        return requested
    for candidate in GROQ_CHAT_PREFERENCE:
        if candidate in ids:
            return candidate
    for model_id in ids:
        lowered = model_id.lower()
        if any(token in lowered for token in GROQ_SKIP_TOKENS):
            continue
        return model_id
    raise RuntimeError("No Groq chat model is available on this API key")


def llm_error_detail(exc: APIError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
    message = str(exc)
    if message.strip():
        return message
    return "The language model request failed."


def _hashed_vector(text: str) -> list[float]:
    vector = [0.0] * LOCAL_EMBED_DIM
    for match in IDENTIFIER.finditer(text.lower()):
        digest = hashlib.blake2b(match.group().encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:2], "little") % LOCAL_EMBED_DIM
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
