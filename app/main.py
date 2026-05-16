from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.auth import get_current_user
import app.models  # noqa: F401 — registers all models with SQLAlchemy
from app.templates import templates
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# Static files
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
app.include_router(auth_router.router)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


# ── Root (temporary — will become dashboard) ───────────────────────────────
@app.get("/")
def root(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request,
        "base.html",
        {"current_user": current_user},
    )