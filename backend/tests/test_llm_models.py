from app.services.llm import (
    GROQ_CHAT_MODEL,
    LOCAL_EMBED_MODEL,
    LocalTokenEmbedder,
    pick_groq_chat_model,
    resolve_models,
)
from app.settings import Settings


def test_groq_uses_local_embeddings_and_remaps_chat() -> None:
    settings = Settings(
        openai_api_key="gsk-test",
        openai_base_url="https://api.groq.com/openai/v1",
        llm_model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
    )
    chat, embed = resolve_models(settings)
    assert chat == GROQ_CHAT_MODEL
    assert embed == LOCAL_EMBED_MODEL


def test_groq_remaps_deprecated_llama_id() -> None:
    settings = Settings(
        openai_api_key="gsk-test",
        openai_base_url="https://api.groq.com/openai/v1",
        llm_model="llama-3.1-8b-instant",
        embedding_model="text-embedding-3-small",
    )
    chat, embed = resolve_models(settings)
    assert chat == GROQ_CHAT_MODEL
    assert embed == LOCAL_EMBED_MODEL


def test_pick_groq_chat_model_skips_audio_and_picks_preference() -> None:
    chosen = pick_groq_chat_model(
        ["whisper-large-v3", "openai/gpt-oss-20b", "canopylabs/orpheus-v1-english"],
        "llama-3.1-8b-instant",
    )
    assert chosen == "openai/gpt-oss-20b"
    settings = Settings(
        openai_api_key="sk-test",
        openai_base_url=None,
        llm_model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
    )
    chat, embed = resolve_models(settings)
    assert chat == "gpt-4o-mini"
    assert embed == "text-embedding-3-small"


def test_local_embedder_is_deterministic() -> None:
    embedder = LocalTokenEmbedder()
    first = embedder.embed(["def authenticate(key: str) -> User:"])
    second = embedder.embed(["def authenticate(key: str) -> User:"])
    assert first == second
    assert abs(sum(value * value for value in first[0]) - 1.0) < 1e-6
