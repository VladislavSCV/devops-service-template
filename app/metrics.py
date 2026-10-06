"""Prometheus metrics and a pure-ASGI middleware that records them and logs each request."""

import logging
import time
import uuid

from prometheus_client import Counter, Gauge, Histogram
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "handler", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "handler"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed.",
    ["method"],
)

# Do not pollute logs with probes and scrapes.
_QUIET_PATHS = {"/health", "/ready", "/metrics"}

log = logging.getLogger("app.access")


class MetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        request_id = _header(scope, b"x-request-id") or uuid.uuid4().hex
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
                message["headers"] = headers
            await send(message)

        # The Prometheus scrape itself is not counted as in-progress work.
        in_progress = IN_PROGRESS.labels(method) if scope["path"] != "/metrics" else None
        if in_progress is not None:
            in_progress.inc()
        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            if in_progress is not None:
                in_progress.dec()
            handler = _handler(scope)
            REQUESTS.labels(method, handler, str(status)).inc()
            LATENCY.labels(method, handler).observe(elapsed)
            if scope["path"] not in _QUIET_PATHS:
                log.info(
                    "request",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "path": scope["path"],
                        "handler": handler,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 2),
                        "client": (scope.get("client") or ("-",))[0],
                    },
                )


def _handler(scope: Scope) -> str:
    """Route template (e.g. /api/items/{item_id}) to keep label cardinality bounded."""
    route = scope.get("route")  # set by FastAPI's APIRoute
    if route is None:
        # Plain Starlette routes (/docs, /openapi.json) do not set scope["route"].
        app = scope.get("app")
        for candidate in getattr(getattr(app, "router", None), "routes", []):
            if candidate.matches(scope)[0] == Match.FULL:
                route = candidate
                break
    return getattr(route, "path", None) or "__unmatched__"


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")[:128]
    return None
