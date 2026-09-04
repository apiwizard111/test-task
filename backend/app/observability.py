from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from typing import Any

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(message, extra={"extra_fields": fields})


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        header_pairs = list(scope.get("headers") or [])
        request_id = _header(header_pairs, b"x-request-id") or str(uuid.uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        started = time.perf_counter()

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
                log_event(
                    logging.getLogger("http"),
                    "request",
                    request_id=request_id,
                    method=scope.get("method"),
                    path=scope.get("path"),
                    status=message.get("status"),
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for key, value in headers:
        if key == name:
            return value.decode()
    return None
