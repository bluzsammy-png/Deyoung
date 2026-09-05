"""FastAPI application factory for the PATI control plane."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, config, db, orchestrator, security, webapp
from .routers import admin, artifacts, connectors, core, research, tasks, workers

log = logging.getLogger("pati")

_shutdown: asyncio.Event | None = None


async def _dispatch_loop():
    """Background loop: refresh task statuses, run the watchdog."""
    assert _shutdown is not None
    while not _shutdown.is_set():
        try:
            await asyncio.to_thread(orchestrator.dispatch_scan)
            await asyncio.to_thread(orchestrator.watchdog)
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                return  # interpreter/server teardown; exit quietly
            log.exception("dispatch loop error: %s", e)
        except Exception as e:  # keep the loop alive no matter what
            log.exception("dispatch loop error: %s", e)
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=2.0)
            break
        except asyncio.TimeoutError:
            continue


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutdown
    db.init_db()
    security.bootstrap_admin_token()
    _shutdown = asyncio.Event()
    task = asyncio.create_task(_dispatch_loop())
    log.info("PATI control plane started (data dir: %s)", config.DATA_DIR)
    yield
    _shutdown.set()
    task.cancel()


class VersionHeaderMiddleware:
    """Pure ASGI middleware (no BaseHTTPMiddleware): adds version headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-pati-version", __version__.encode()))
                t0 = scope.get("pati_t0")
                if t0:
                    headers.append((b"x-pati-trace-time-ms",
                                    f"{(time.time()-t0)*1000:.1f}".encode()))
            await send(message)

        scope["pati_t0"] = time.time()
        await self.app(scope, receive, send_wrapper)


def create_app() -> FastAPI:
    app = FastAPI(
        title="PATI Control Plane",
        description="Personal AI Tool Infrastructure - zero-cost AI infrastructure layer. "
                    "FREE_ONLY=true; every registry entry has cost=0.",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    app.add_middleware(VersionHeaderMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "error": {"code": "SCHEMA_VALIDATION", "message": "request failed schema validation",
                      "detail": exc.errors()[:10]}})

    from .security import PATIError

    @app.exception_handler(PATIError)
    async def pati_error_handler(request: Request, exc: PATIError):
        return JSONResponse(status_code=exc.status,
                            content={"error": {"code": exc.code, "message": exc.message}})

    # ------------------------------------------------------------ web pages
    def _base(request: Request) -> str:
        return str(request.base_url).rstrip("/")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root(request: Request):
        return webapp.render_dashboard(_base(request))

    @app.get("/faq", response_class=HTMLResponse, include_in_schema=False)
    def faq(request: Request):
        return webapp.render_faq(_base(request))

    @app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
    def privacy(request: Request):
        return webapp.render_privacy(_base(request))

    @app.get("/thank-you", response_class=HTMLResponse, include_in_schema=False)
    def thank_you(request: Request, job: str = ""):
        return webapp.render_thanks(_base(request), job)

    @app.get("/offline", response_class=HTMLResponse, include_in_schema=False)
    def offline():
        return webapp.render_offline()

    @app.get("/robots.txt", include_in_schema=False)
    def robots():
        return PlainTextResponse(webapp.robots_txt())

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request):
        return Response(webapp.sitemap_xml(_base(request)), media_type="application/xml")

    @app.get("/llms.txt", include_in_schema=False)
    def llms(request: Request):
        return PlainTextResponse(webapp.llms_txt(_base(request)))

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return Response(webapp.manifest_json(), media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return Response(webapp.sw_js(), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})

    @app.get("/owner-photo.png", include_in_schema=False)
    def owner_photo():
        p = config.DATA_DIR / "owner-photo.png"
        if not p.exists():  # neutral placeholder instead of a console-error 404
            p = config.PACKAGE_DIR / "static" / "avatar-default.png"
        return Response(p.read_bytes(), media_type="image/png")

    static_dir = config.PACKAGE_DIR / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")

    # custom 404 page (HTML for pages, JSON for API paths)
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/assets/")):
            return HTMLResponse(status_code=404,
                                content=webapp.render_404(_base(request), request.url.path))
        headers = getattr(exc, "headers", None) or {}
        return JSONResponse(status_code=exc.status_code,
                            content={"error": {"code": f"HTTP_{exc.status_code}",
                                               "message": str(exc.detail)}},
                            headers=headers)

    prefix = config.API_PREFIX
    app.include_router(core.router, prefix=prefix, tags=["core"])
    # Master-prompt canonical root-level aliases (GET /health, /capabilities, ...)
    app.include_router(core.router, prefix="", include_in_schema=False)
    app.include_router(tasks.router, prefix=prefix, tags=["tasks"])
    app.include_router(workers.router, prefix=prefix, tags=["workers"])
    app.include_router(artifacts.router, prefix=prefix, tags=["artifacts"])
    app.include_router(research.router, prefix=prefix, tags=["research"])
    app.include_router(connectors.router, prefix=prefix, tags=["connectors"])
    app.include_router(admin.router, prefix=prefix, tags=["admin"])
    return app


app = create_app()
