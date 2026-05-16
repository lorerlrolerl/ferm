from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import create_tables
import app.models  # noqa: F401 — registers all models with SQLAlchemy

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

# Templates — settings injected as global so every template can use it
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["settings"] = settings


@app.on_event("startup")
def on_startup():
    create_tables()


# ── Routers ────────────────────────────────────────────────────────────────
# from app.routers import dashboard, ferments, ingredients
# app.include_router(dashboard.router)
# app.include_router(ferments.router)
# app.include_router(ingredients.router)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


# ── Root ───────────────────────────────────────────────────────────────────
@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request, "base.html")