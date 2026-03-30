# app/middleware/logging_middleware.py
import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from app.core.logging_config import get_logger

logger = get_logger("app.http")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request and outgoing response.
    Shows method, path, status code, duration, and body (if JSON).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()

        # ── Log request ───────────────────────────────────────────────────────
        body_bytes = await request.body()
        body_str = ""
        if body_bytes:
            try:
                body_data = json.loads(body_bytes)
                # Mask sensitive fields
                for field in ("password", "confirm_password", "new_password"):
                    if field in body_data:
                        body_data[field] = "***"
                body_str = json.dumps(body_data, ensure_ascii=False)
            except Exception:
                body_str = body_bytes.decode("utf-8", errors="replace")[:500]

        logger.info(
            f"→ {request.method} {request.url.path}"
            + (f" | body: {body_str}" if body_str else "")
            + f" | client: {request.client.host if request.client else 'unknown'}"
        )

        # ── Call the actual endpoint ──────────────────────────────────────────
        # We need to re-inject the body since we consumed it above
        async def receive() -> Message:
            return {"type": "http.request", "body": body_bytes}

        request._receive = receive  # type: ignore[attr-defined]

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000

        # ── Log response ──────────────────────────────────────────────────────
        level = logger.info if response.status_code < 400 else logger.warning
        if response.status_code >= 500:
            level = logger.error

        level(
            f"← {request.method} {request.url.path} "
            f"| status: {response.status_code} "
            f"| {duration_ms:.1f}ms"
        )

        return response