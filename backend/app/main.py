"""Credit Agent Squad API."""
from fastapi import APIRouter, FastAPI

from app.api import auth, routes_credit, routes_work

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title="Credit Agent Squad", version="0.1.0", redirect_slashes=False)
    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(auth.router)
    api.include_router(routes_credit.router)
    api.include_router(routes_work.router)
    app.include_router(api)
    return app


app = create_app()
