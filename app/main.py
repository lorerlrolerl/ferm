from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.templates import templates  # noqa: F401
import app.models  # noqa: F401

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.on_event("startup")
def on_startup():
    create_tables()


# ── Routers ────────────────────────────────────────────────────────────────
from app.routers import auth as auth_router
from app.routers import dashboard as dashboard_router
from app.routers import ferments as ferments_router
from app.routers import batches as batches_router
from app.routers import ingredients as ingredients_router
from app.routers import additives as additives_router

app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(ferments_router.router)
app.include_router(batches_router.router)
app.include_router(ingredients_router.router)
app.include_router(additives_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}