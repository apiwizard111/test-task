from fastapi import APIRouter, Request

from app.services.llm import resolve_models
from app.services.store import Store
from app.settings import Settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, bool | str]:
    store: Store = request.app.state.store
    settings: Settings = request.app.state.settings
    llm_configured: bool = request.app.state.llm is not None
    provider = "none"
    llm_model = ""
    embedding_model = ""
    if llm_configured:
        host = (settings.openai_base_url or "").lower()
        if "groq.com" in host:
            provider = "groq"
        elif settings.openai_base_url:
            provider = "custom"
        else:
            provider = "openai"
        llm_model, embedding_model = resolve_models(settings)
        gateway = request.app.state.llm
        resolved = getattr(gateway, "chat_model", None)
        if isinstance(resolved, str) and resolved.strip():
            llm_model = resolved
    return {
        "ingested": store.is_ready,
        "llm_configured": llm_configured,
        "name": store.manifest.name if store.manifest else "",
        "provider": provider,
        "llm_model": llm_model,
        "embedding_model": embedding_model,
    }
