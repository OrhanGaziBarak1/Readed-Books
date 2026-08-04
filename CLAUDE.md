# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

An experiment in controlling a backend entirely through natural language via Claude. The plan:

1. Build FastAPI endpoints for a personal "read books" database (migrating book data out of Microsoft Loop into PostgreSQL).
2. For each API endpoint, add a matching FastMCP tool so Claude can drive the same operations conversationally.

This is a learning/experimental project — favor clarity and small working increments over robustness or premature abstraction.

## Commands

- Run the dev server: `uv run uvicorn readedbooks.main:app --reload`
- Run the CLI entry point: `uv run readedbooks`
- Install/sync dependencies: `uv sync`
- Add a dependency: `uv add <package>`

This project uses **uv** for all dependency and environment management — do not use `pip` or `poetry` directly.

## Current state

- No linter, formatter, or test suite is configured yet. Don't assume `ruff`, `black`, `mypy`, or `pytest` are available until they're added as dev dependencies.
- Requires Python 3.14 (see `.python-version`).
- PostgreSQL is wired up via SQLModel + Alembic (`alembic/`, `src/readedbooks/db.py`).
- Shared services layer (`exceptions.py`, `services.py`) is implemented — see below.

## Architecture plan: shared services layer

FastMCP tools must not call the FastAPI endpoints over HTTP — that would mean the same process making a network call to itself. Instead, DB/business logic is pulled out into a shared layer that both FastAPI routes and FastMCP tools call in-process:

```
src/readedbooks/
├── main.py          # FastAPI app: routes only, translate HTTP <-> services.py
├── mcp_server.py     # FastMCP app: tools only, translate MCP <-> services.py (not yet built)
├── services.py       # Shared DB/business logic — no FastAPI or FastMCP imports
├── exceptions.py      # Plain Python exceptions (e.g. NotFoundError) + their HTTP-agnostic message logic — no HTTP knowledge
├── models.py
└── db.py
```

- `exceptions.py` holds plain-Python domain exceptions (`NotFoundError`) with no HTTP or MCP awareness, plus the `UNIQUE_CONSTRAINT_MESSAGES` mapping and `integrity_error_message()` helper used to turn a raw `sqlalchemy.exc.IntegrityError` into a user-facing message.
- `services.py` holds the actual query/mutation logic and raises those domain exceptions (e.g. `get_book` raises `NotFoundError` if missing).
- `main.py` is thin route handlers that call `services.py`, plus two global handlers: `@app.exception_handler(NotFoundError)` (→ 404) and `@app.exception_handler(IntegrityError)` (→ 409, via `integrity_error_message()`). No more per-route `if x is None: raise HTTPException(...)`.
- `mcp_server.py` (not built yet) will call the same `services.py` functions and translate `NotFoundError` into whatever error shape FastMCP tools use.

**Why:** avoids duplicating logic between the API and MCP tools, and avoids MCP tools making self-referential HTTP calls. A single domain exception (e.g. `NotFoundError`) is defined once and translated independently by each protocol layer (HTTP status vs. MCP tool error). Exception *handlers* stay protocol-specific (in `main.py` for HTTP) since they can't be shared with `mcp_server.py`'s own translation layer.

**Status:** `exceptions.py` and `services.py` are implemented — `main.py` route bodies now just call `services.py`. `mcp_server.py` is still not built.
