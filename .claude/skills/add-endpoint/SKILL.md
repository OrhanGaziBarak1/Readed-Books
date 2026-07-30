---
name: add-endpoint
description: Add a new FastAPI endpoint to readedbooks paired with a matching FastMCP tool. Use when the user wants to add a new API route (e.g. a new books/CRUD operation) so Claude can also drive it conversationally via MCP.
---

Every FastAPI endpoint in this project should have a matching FastMCP tool that wraps it, so the same operation is reachable both over HTTP and through natural-language chat with Claude.

When adding a new endpoint:

1. Add the FastAPI route in `src/readedbooks/main.py` (or a router module if one exists by then). Use clear request/response types (Pydantic models) rather than raw dicts once the data model exists.
2. Add a corresponding FastMCP tool function that calls the same underlying logic the endpoint uses — don't duplicate business logic between the HTTP handler and the MCP tool; factor shared logic into a plain function both call.
3. Keep tool names and descriptions specific enough that Claude can pick the right one in conversation (e.g. `add_book`, `list_books_by_status`, not generic names like `run_query`).
4. If the endpoint touches the database, keep the query logic isolated from the route/tool wiring so it's easy to test once a test suite exists.

Ask the user for the exact route/operation they want before writing code if it's not already clear (path, method, request/response shape).
