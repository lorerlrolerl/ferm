# ferm

Professional fermentation kitchen tracker.

## Stack

- **Python 3.12** — managed with [uv](https://docs.astral.sh/uv/)
- **FastAPI** — API and server-rendered pages
- **SQLAlchemy 2** — ORM (SQLite in dev, Postgres-ready)
- **Jinja2** — templating
- **HTMX** — frontend interactivity without a JS framework

## Setup

```bash
# Clone and enter
git clone https://github.com/lorerlrolerl/ferm.git
cd ferm

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install deps
uv sync

# Copy env file and set your values
cp .env.example .env

# Run the dev server
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 — you should see the ferm shell.

## Project structure

```
app/
├── main.py          # FastAPI app, startup, router registration
├── config.py        # Settings from environment
├── database.py      # SQLAlchemy engine, session, Base
├── models/          # One file per domain model
├── routers/         # One file per feature area
├── templates/       # Jinja2 HTML templates
└── static/          # CSS, JS
```

## Development

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .
```