"""Credit Agent Squad API."""
import importlib

from fastapi import APIRouter, FastAPI

from app.api import auth, routes_credit, routes_work
from app.domain import hooks  # noqa: F401  (registers decision hooks)

API_PREFIX = "/api/v1"
# Routers added by later milestones. Each is included when its module exists, so no one has
# to edit this file to add a router: create `app/api/<name>.py` with a `router`.
OPTIONAL_ROUTERS = ("routes_ui", "routes_reviews", "routes_packages", "routes_copilot", "routes_evals")


def create_app() -> FastAPI:
    app = FastAPI(title="Credit Agent Squad", version="0.1.0", redirect_slashes=False)
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
