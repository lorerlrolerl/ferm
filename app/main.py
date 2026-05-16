from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.templates import templates  # noqa: F401 — ensures globals are set
import app.models  # noqa: F401 — registers all models with SQLAlchemy

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

app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(ferments_router.router)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}