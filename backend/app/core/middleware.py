"""ASGI middleware: early upload size limits and security headers."""

from __future__ import annotations

from collections.abc import Callable

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

UPLOAD_PATH = "/api/scans/upload"
MULTIPART_OVERHEAD_BYTES = 64 * 1024

class BodyTooLarge(Exception):
    """Raised inside the request stream once the body exceeds the limit."""

class UploadLimitMiddleware:
    """Reject oversized uploads before they are fully written to disk.

    Checks Content-Length up front, and also counts streamed bytes for requests that
    declare no length (chunked uploads). The route still enforces the exact file limit.
    """

    def __init__(self, app: ASGIApp, limit: Callable[[], int], path: str = UPLOAD_PATH) -> None:
        self.app = app
        self.limit = limit
        self.path = path

    async def _respond(self, scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.path:
            await self.app(scope, receive, send)
            return

        max_bytes = self.limit()
        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                too_large = int(declared) > max_bytes
            except ValueError:
                await self._respond(scope, receive, send, 400, "Invalid Content-Length header.")
                return
            if too_large:
                await self._respond(scope, receive, send, 413, "Upload exceeds the maximum allowed size.")
                return

        received = 0
        response_started = False
        buffered: list[Message] = []
        while declared is None:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > max_bytes:
                await self._respond(scope, receive, send, 413, "Upload exceeds the maximum allowed size.")
                return
            if not message.get("more_body", False):
                break

        replay_index = 0

        async def limited_receive() -> Message:
            nonlocal replay_index, received
            if declared is None and replay_index < len(buffered):
                message = buffered[replay_index]
                replay_index += 1
                return message
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            if response_started:
                raise
            await self._respond(scope, receive, send, 413, "Upload exceeds the maximum allowed size.")

class SecurityHeadersMiddleware:
    """Add conservative security headers to every response (never overriding existing ones)."""

    HEADERS = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "cache-control": "no-store",
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)
