"""Credit Agent Squad API."""
import importlib

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api import auth, routes_credit, routes_work
from app.core.config import MAX_UPLOAD_BYTES, get_settings
from app.domain import hooks  # noqa: F401  (registers decision hooks)

API_PREFIX = "/api/v1"
# Routers added by later milestones. Each is included when its module exists, so no one has
# to edit this file to add a router: create `app/api/<name>.py` with a `router`.
OPTIONAL_ROUTERS = ("routes_ui", "routes_reviews", "routes_packages", "routes_copilot", "routes_evals",
                    "routes_governance", "routes_squad")


class RefuseOversizedUploads:
    """Refuse a request whose declared body is larger than an upload may be, before any of it is
    read. A body sent without a declared length is counted as it is read, in the upload route."""

    def __init__(self, app: ASGIApp, limit: int):
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH"):
            declared = dict(scope["headers"]).get(b"content-length", b"")
            if declared.isdigit() and int(declared) > self.limit:
                response = JSONResponse({"detail": too_large_message()}, status_code=413)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def too_large_message() -> str:
    return f"The file is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit for an upload."


def create_app() -> FastAPI:
    settings = get_settings()
    # the interactive documentation lists every route, so it is served only where a setting allows it
    docs = settings.serve_api_docs
    app = FastAPI(title="Credit Agent Squad", version="0.1.0", redirect_slashes=False,
                  docs_url="/docs" if docs else None, redoc_url="/redoc" if docs else None,
                  openapi_url="/openapi.json" if docs else None)
    # a multipart body carries a little more than the file itself
    app.add_middleware(RefuseOversizedUploads, limit=MAX_UPLOAD_BYTES + 64 * 1024)
    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(auth.router)
    api.include_router(routes_credit.router)
    api.include_router(routes_work.router)
    for name in OPTIONAL_ROUTERS:
        try:
            module = importlib.import_module(f"app.api.{name}")
        except ModuleNotFoundError as exc:
            if exc.name != f"app.api.{name}":
                raise  # the module exists but one of its own imports is missing: do not hide that
            continue
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
