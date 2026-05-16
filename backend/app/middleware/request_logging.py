"""Pure-ASGI request logging middleware.

Generates a request_id UUID for every HTTP request and binds it to the
structlog contextvars context so all logs emitted during the request
automatically carry request_id.

Uses raw ASGI (not BaseHTTPMiddleware) to avoid known streaming issues
in Starlette's BaseHTTPMiddleware when responses are streamed.
"""

import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import structlog

log = structlog.get_logger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        method = scope.get("method", "")
        path = scope.get("path", "")
        # Deliberately omit query_string — tokens can appear there.

        start = time.perf_counter()
        status_code = 0

        async def send_wrapper(message: Any) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            log.info("http.request", method=method, path=path)
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            log.info(
                "http.response",
                method=method,
                path=path,
                status=status_code,
                duration_ms=duration_ms,
            )
