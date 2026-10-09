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

Tools usable conversationally from Claude Desktop (or any other MCP client). Book and author tools work by **name** (`Book.name` + `Author.name`, `Author.name`) rather than by id, since the user doesn't know ids. Update and delete match the name exactly; the list tools match partially and case-insensitively.

- `list_books_tool` (optional filters: `name`, `author_name`, `status`, `language`), `create_book_tool`, `update_book_tool`, `delete_book_tool`
- `list_authors_tool` (optional filter: `name`), `create_author_tool`, `update_author_tool`, `delete_author_tool`

Both list tools are paginated (`page`, `page_size` up to 100) and return a `Page` object: `items`, `page`, `page_size`, `count`, `total`, `total_pages`. Books in `items` use a `BookRead` schema with `author_name` instead of `author_id`.

### Connecting Claude Desktop

Claude Desktop reads its MCP servers from a file called `claude_desktop_config.json`. Its location depends on the OS:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` (usually `C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json`) |
| Linux | `~/.config/Claude/claude_desktop_config.json` (or `$XDG_CONFIG_HOME/Claude/...` if that variable is set) |

You can also open it from the app: **Settings → Developer → Edit Config**. If the file doesn't exist yet, launch Claude Desktop once so it creates it.

> The macOS path is the one verified for this project. The Windows and Linux paths come from public setup guides and were not tested here. The [official Linux guide](https://code.claude.com/docs/en/desktop-linux) doesn't state where the config file lives, so if `~/.config/Claude/claude_desktop_config.json` doesn't exist on your machine, use **Settings → Developer → Edit Config** to find the real location.

If the file already has other keys (e.g. `preferences`), don't replace it. Add only the `readedbooks` entry inside `mcpServers` (create `mcpServers` if it's missing):

```json
{
  "mcpServers": {
    "readedbooks": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--project", "/path/to/readedBooks",
        "--with", "fastmcp",
        "--with-editable", "/path/to/readedBooks",
        "fastmcp", "run", "/path/to/readedBooks/src/readedbooks/main.py:mcp_app"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost:5432/dbname"
      }
    }
  }
}
```

Replace the placeholders:

- **`/path/to/uv`**: the full path to `uv`. Find it with `which uv` (macOS/Linux) or `where uv` (Windows). Claude Desktop's PATH can differ from your terminal's, so a bare `uv` may not resolve.
- **`/path/to/readedBooks`**: the absolute path of this repository.
- **Windows paths in JSON**: use forward slashes (`C:/Users/you/readedBooks`) or double every backslash (`C:\\Users\\you\\readedBooks`). A single backslash is invalid JSON.
- **`env.DATABASE_URL`**: required, because Claude Desktop launches the process from its own working directory, not the project directory where `.env` lives. This file stores your database password in plain text, so don't commit or share it.

After saving, fully quit Claude Desktop and reopen it: `Cmd+Q` on macOS; on Windows exit it from the system tray icon, since closing the window may only minimize it; on Linux quit the app and start it again with `claude-desktop`.

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

For detailed architecture notes, design decisions, see [CLAUDE.md](./CLAUDE.md).
