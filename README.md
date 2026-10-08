# readedbooks

A personal "read books" database (migrated from Microsoft Loop into PostgreSQL), managed both through a FastAPI HTTP API and conversationally via Claude. Every FastAPI endpoint has a matching FastMCP tool, so the same operations can be triggered over HTTP or through chat.

This is a learning/experimental project — favor clarity and small working increments over robustness.

## Setup

The project uses [uv](https://docs.astral.sh/uv/) for all dependency and environment management — no `pip`/`poetry`.

```bash
uv sync
```

Requires Python 3.14 (see `.python-version`).

### Database

PostgreSQL + SQLModel + Alembic. Create a `.env` file in the project root with the connection string:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Running

```bash
# FastAPI dev server
uv run uvicorn readedbooks.main:app --reload

# CLI entry point
uv run readedbooks

# MCP server (stdio) — the same command Claude Desktop launches
uv run fastmcp run src/readedbooks/main.py:mcp_app
```

With the server running, Swagger UI is available at `http://127.0.0.1:8000/docs`.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/books` | List books (dynamic filtering + limit/offset) |
| GET | `/books/{book_id}` | Get a single book |
| POST | `/books` | Create a book |
| PATCH | `/books/{book_id}` | Update a book |
| DELETE | `/books/{book_id}` | Delete a book |
| POST | `/books/import` | Bulk import books/authors from a CSV file |
| GET | `/authors` | List authors (dynamic filtering + limit/offset) |
| GET | `/authors/{author_id}` | Get a single author |
| POST | `/authors` | Create an author |
| PATCH | `/authors/{author_id}` | Update an author |
| DELETE | `/authors/{author_id}` | Delete an author |

### CSV import format

Columns expected in `readedbooks.csv`:

```
Kitap Adı, Sayfa Sayısı, Okuma Durumu, Dil, Yazarlar
```

`Okuma Durumu` (reading status): `Okudum` (read) / `Okumadım` (unread) / `Okuyorum` (reading)
`Dil` (language): `Türkçe` (Turkish) / `İngilizce` (English)

If an author name doesn't match an existing one, it's created automatically. A failing row doesn't abort the import — the result reports how many rows were created and which ones were skipped, with the reason.

## MCP Tools

Tools usable conversationally from Claude Desktop (or any other MCP client). Book and author tools work by **name** (`Book.name` + `Author.name`, `Author.name`) rather than by id, since the user doesn't know ids.

- `list_books_tool`, `get_book_tool`, `create_book_tool`, `update_book_tool`, `delete_book_tool`
- `list_authors_tool`, `get_author_tool`, `create_author_tool`, `update_author_tool`, `delete_author_tool`

Tools that return books use a `BookRead` schema with `author_name` instead of `author_id`.

### Connecting Claude Desktop

Add this to `claude_desktop_config.json` (Settings → Developer → Edit Config, or the connector-adding screen in the UI):

```json
{
  "mcpServers": {
    "readedbooks": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--project", "/path/to/readed-book",
        "--with", "fastmcp",
        "--with-editable", "/path/to/readed-book",
        "fastmcp", "run", "/path/to/readed-book/src/readedbooks/main.py:mcp_app"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost:5432/dbname"
      }
    }
  }
}
```

Find the full path to `uv` with `which uv` — Claude Desktop's PATH can differ from your terminal's. The `env` block is required because Claude Desktop launches the process from its own working directory, not the project directory where `.env` lives.

After configuring, fully quit Claude Desktop (Cmd+Q) and reopen it.

### Standalone testing

```bash
# Call tools interactively in the browser (requires Node.js/npx)
uv run fastmcp dev inspector src/readedbooks/main.py:mcp_app
```

To tail Claude Desktop's logs:

```bash
tail -f ~/Library/Logs/Claude/mcp-server-readedbooks.log
```

## Architecture

For detailed architecture notes, design decisions, and open TODOs, see [CLAUDE.md](./CLAUDE.md).
