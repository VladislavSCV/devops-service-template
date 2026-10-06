"""Application factory. Run with: uvicorn --factory app.main:create_app"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.concurrency import run_in_threadpool
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import __version__, db
from app.config import Settings, get_settings
from app.items import router as items_router
from app.logging_config import setup_logging
from app.metrics import MetricsMiddleware

log = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    db.init_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        log.info("startup", extra={"version": __version__, "environment": settings.environment})
        yield
        # Uvicorn stops accepting connections and drains in-flight requests on SIGTERM
        # before this runs; here we only release resources.
        db.dispose_engine()
        log.info("shutdown complete")

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.add_middleware(MetricsMiddleware)
    app.include_router(items_router)
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness: the process is up and serving requests."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready(response: Response) -> dict[str, str]:
        """Readiness: dependencies (the database) are reachable."""
        try:
            await run_in_threadpool(db.ping)
        except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
            log.warning("readiness check failed", extra={"error": str(exc)})
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unavailable", "database": "error"}
        return {"status": "ok", "database": "ok"}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
