from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import APIError

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.sources import router as sources_router
from app.observability import RequestIdMiddleware, configure_logging
from app.services.github import GithubIngestError
from app.services.ingest import IngestError, IngestService
from app.services.llm import LlmGateway, OpenAiGateway, llm_error_detail
from app.services.rag import RagService
from app.services.retrieve import RetrieveService
from app.services.store import Store
from app.settings import Settings, get_settings


def create_app(settings: Settings | None = None, llm: LlmGateway | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = Store(Path(resolved.data_dir))
        store.initialize()
        gateway = llm
        if gateway is None:
            gateway = _maybe_openai(resolved)
        ingest = None
        rag = None
        if gateway is not None:
            ingest = IngestService(store, gateway, Path(resolved.sample_repo_dir))
            retriever = RetrieveService(store, gateway)
            rag = RagService(retriever, gateway, debug=resolved.debug_retrieval)
        app.state.settings = resolved
        app.state.store = store
        app.state.llm = gateway
        app.state.ingest = ingest
        app.state.rag = rag
        yield

    app = FastAPI(title="RepoLens", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(ingest_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")

    @app.exception_handler(IngestError)
    async def ingest_error_handler(_request: Request, exc: IngestError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(GithubIngestError)
    async def github_error_handler(_request: Request, exc: GithubIngestError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(APIError)
    async def llm_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": llm_error_detail(exc)})

    return app


def _maybe_openai(settings: Settings) -> LlmGateway | None:
    key = settings.openai_api_key.strip()
    if not key or key.startswith("sk-your-key"):
        return None
    return OpenAiGateway(settings)


app = create_app()
