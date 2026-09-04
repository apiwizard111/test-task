from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest
from app.observability import request_id_of
from app.services.rag import RagService
from app.services.store import Store

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    store: Store = request.app.state.store
    rag: RagService | None = request.app.state.rag
    if rag is None:
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY before chatting")
    if not store.is_ready:
        raise HTTPException(status_code=409, detail="Ingest a repository before asking questions")

    async def events():
        async for chunk in rag.stream_answer(
            payload.message,
            payload.history,
            request_id_of(request),
            paths=payload.paths,
        ):
            yield chunk

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
