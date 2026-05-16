from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import settings
from app.database import create_tables

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

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.on_event("startup")
def on_startup():
    create_tables()


# ── Routers ────────────────────────────────────────────────────────────────
# from app.routers import dashboard, ferments, ingredients
# app.include_router(dashboard.router)
# app.include_router(ferments.router)
# app.include_router(ingredients.router)


# ── Temporary health check ─────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


# ── Temporary root ─────────────────────────────────────────────────────────
from fastapi import Request

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})