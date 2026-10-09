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
- Run the MCP server over stdio (what Claude Desktop launches): `uv run fastmcp run src/readedbooks/main.py:mcp_app`
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
├── main.py          # FastAPI routes + FastMCP tools (`mcp_app`), both thin wrappers over services.py
├── services.py       # Shared DB/business logic — no FastAPI or FastMCP imports
├── exceptions.py      # Plain Python exceptions (e.g. NotFoundError) + their HTTP-agnostic message logic — no HTTP knowledge
├── models.py
└── db.py
```

- `exceptions.py` holds plain-Python domain exceptions (`NotFoundError`) with no HTTP or MCP awareness, plus the `CONSTRAINT_MESSAGES` mapping (unique and foreign-key constraint names → user-facing messages) and `integrity_error_message()` helper used to turn a raw `sqlalchemy.exc.IntegrityError` into a user-facing message.
- `services.py` holds the actual query/mutation logic and raises those domain exceptions (e.g. `get_book` raises `NotFoundError` if missing).
- `main.py` route bodies just call `services.py`, plus two global handlers: `@app.exception_handler(NotFoundError)` (→ 404) and `@app.exception_handler(IntegrityError)` (→ 409, via `integrity_error_message()`). No more per-route `if x is None: raise HTTPException(...)`.
- MCP tools (`@mcp_app.tool()`) live in `main.py` too and also just call `services.py`. Each tool opens its own `Session(engine)`, because FastAPI's `Depends` does not run for MCP calls. MCP tools do not translate exceptions; FastMCP wraps a raised exception into a `ToolError` carrying its message.

**Why:** avoids duplicating logic between the API and MCP tools, and avoids MCP tools making self-referential HTTP calls. A single domain exception (e.g. `NotFoundError`) is defined once and translated independently by each protocol layer (HTTP status vs. MCP tool error). Exception *handlers* stay protocol-specific (in `main.py` for HTTP) since the MCP layer has no equivalent of HTTP status codes.

**Status:** `exceptions.py` and `services.py` are implemented. MCP tools are implemented in `main.py` (whether they should move to `mcp_server.py` as originally planned is undecided).

## Decisions

- **MCP tools address books by `(name, author_name)` and authors by `name`, never by id.** Users don't know ids. This is safe because `uq_book_name_author_id` and `uq_author_name` make these unique. Lookups live in `services.get_book_by_name` / `services.get_author_by_name`.
- **`list_books_tool` is the single read/search tool for books (there is no `get_book_tool`).** Every filter is optional (nothing required), combined with AND: `name`/`author_name` (partial, case-insensitive `ILIKE '%...%'`, `%`/`_` escaped), `status`, `language`. Filters are typed parameters per column (not a generic field/operator DSL); date and length filters were deliberately dropped. It is paginated with `page` (1-based, `ge=1`) and `page_size` (1-100, default 20) and returns a generic `Page[BookRead]` envelope (`Page[T]` in `models.py`, reusable for other list tools; it extends plain pydantic `BaseModel`, not `SQLModel`, because with `SQLModel` the type parameter was dropped and `items` had an untyped `{}` schema in the MCP output schema): `items` (`list[T]`), `page`, `page_size`, `count` (items on this page), `total` (all matches for the filters), `total_pages`. A page past the end returns empty `items`, not an error. Pages are stable because `services.paginate` itself orders by the model's primary key (it takes the model class as an argument), so callers cannot forget it and `build_books_query` has no `order_by`. SQLAlchemy 2.0 has no Django-style `Meta.ordering` (`__mapper_args__ order_by` was removed) and Postgres has no default table order, so this has to live in the query layer. Query building is `services.build_books_query`, paging/counting is the generic `services.paginate(session, model, query, page, page_size, to_item)`; the HTTP route still uses `QueryBuilder` and its own `limit`/`offset`. `update_book_tool` / `delete_book_tool` still use the exact `services.get_book_by_name`, because mutations must target one unambiguous book.
- **`list_authors_tool` mirrors `list_books_tool` (there is no `get_author_tool`).** Optional `name` filter (partial, case-insensitive), `page`/`page_size`, returns `Page[Author]`. Query building is `services.build_authors_query`; paging goes through the same `services.paginate`. `update_author_tool` / `delete_author_tool` still use the exact `services.get_author_by_name`.
- **MCP tool names end in `_tool`** (`list_books_tool`, `list_authors_tool`, …). Without the suffix they would share names with the HTTP route functions in `main.py` and shadow them.
- **MCP book responses use `BookRead`** (`author_name` instead of `author_id`). HTTP routes still return `Book`.
- **`create_book_tool` takes `author_name` and creates the author if it doesn't exist** — same behavior as CSV import (`services.get_or_create_author`).
- **`update_book_tool` fills in `author_id` from the existing book** when the caller doesn't send one. This is a workaround for the `services.update_book` gap (it requires `author_id` on every call).
- **Timestamps:** columns are `timestamp without time zone` and hold UTC values. `Book` and `BookRead` serialize them with a `+00:00` offset via `field_serializer`, because MCP hosts validate `date-time` strictly and reject offset-less strings. Changing the column type is deferred.
- **Foreign key name is explicit:** `Book.author_id` uses `ForeignKey("author.id", name="fk_book_author_id")`, so `CONSTRAINT_MESSAGES` does not depend on Postgres' default name `book_author_id_fkey`. Migration `8bc54ef31940` renames the existing constraint.
- **CSV import** (`POST /books/import`) uses pandas. Column names are in `CsvColumns`; status/language mappings are `CSV_STATUS_MAP` / `CSV_LANGUAGE_MAP` in `services.py`. Each row commits on its own; a failing row is rolled back and reported in `errors` instead of aborting the import. The author cell is stored verbatim.
