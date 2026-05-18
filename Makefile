# ferm — development commands
# Usage: make <target>

.PHONY: run seed reset backup restore lint lint-fix test test-cov install docs help

## Start the development server
run:
	uv run uvicorn app.main:app --reload

## Seed the database with default data
seed:
	uv run python -m app.seed

## Backup the current database
backup:
	uv run python -m app.backup

## List backups and restore one interactively
restore:
	uv run python -m app.backup restore

## List all backups
backup-list:
	uv run python -m app.backup list

## Backup, then delete and reseed the database from scratch
reset:
	uv run python -m app.backup
	rm -f ferm.db
	uv run python -m app.seed

## Run linter
lint:
	uv run ruff check .
	uv run ruff format --check .

## Fix lint issues automatically
lint-fix:
	uv run ruff check --fix .
	uv run ruff format .

## Run tests
test:
	uv run pytest tests/ -v

## Run tests with coverage report
test-cov:
	uv run pytest tests/ -v --cov=app --cov-report=term-missing

## Install all dependencies (including dev)
install:
	uv sync --all-extras

## Open API docs in browser (requires server running)
docs:
	open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs

## Show available commands
help:
	@echo ""
	@echo "  ferm — available commands"
	@echo ""
	@grep -E '^##' Makefile | sed 's/## /    /'
	@echo ""