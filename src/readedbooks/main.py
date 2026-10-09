from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from readedbooks import services
from readedbooks.db import engine, get_session
from readedbooks.exceptions import NotFoundError, integrity_error_message
from readedbooks.models import (
    Author,
    AuthorCreateUpdate,
    Book,
    BookCreate,
    BookImportResult,
    BookRead,
    BookUpdate,
    Language,
    Page,
    Status,
)
from fastapi_querybuilder import QueryBuilder
from fastmcp import FastMCP

app = FastAPI()
mcp_app = FastMCP("ReadedBooksMCPServer",
              instructions="Provides tools manage my readed books database.")


@app.exception_handler(IntegrityError)
def handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": integrity_error_message(exc)})


@app.exception_handler(NotFoundError)
def handle_not_found_error(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})

SessionDep = Annotated[Session, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]


@app.get("/books")
def list_books(
    session: SessionDep,
    query=QueryBuilder(Book),
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> list[Book]:
    return services.list_books(session, query, limit, offset)


@mcp_app.tool()
def list_books_tool(
    name: str | None = None,
    author_name: str | None = None,
    status: Status | None = None,
    language: Language | None = None,
    page: Annotated[int, Field(ge=1)] = 1,
    page_size: Annotated[int, Field(ge=1, le=100)] = 20,
) -> Page[BookRead]:
    """List books, optionally filtered. Every filter is optional and filters combine with AND.
    `name` and `author_name` are partial, case-insensitive matches. The result is paginated:
    `items` holds the books on the requested `page` (1-based), `count` is how many items this
    page holds, `total` is how many books match the filters overall, and `total_pages` is the
    number of pages at this `page_size`. If `page` is past `total_pages`, `items` is empty;
    request the next page by increasing `page`."""
    with Session(engine) as session:
        query = services.build_books_query(name, author_name, status, language)
        return services.paginate(
            session, Book, query, page, page_size, lambda book: services.to_book_read(session, book)
        )


@app.post("/books/import")
def import_books(session: SessionDep, file: UploadFile) -> BookImportResult:
    return services.import_books_from_csv(session, file.file)


@app.get("/books/{book_id}")
def get_book(session: SessionDep, book_id: int) -> Book:
    return services.get_book(session, book_id)


@app.post("/books", status_code=201)
def create_book(session: SessionDep, book: BookCreate) -> Book:
    return services.create_book(session, book)

@mcp_app.tool()
def create_book_tool(
    name: str,
    length: int,
    status: Status,
    language: Language,
    author_name: str,
) -> BookRead:
    """Create a new book. The author is looked up by name, or created if they don't exist yet."""
    with Session(engine) as session:
        author = services.get_or_create_author(session, author_name)
        book = BookCreate(name=name, length=length, status=status, language=language, author_id=author.id)
        created_book = services.create_book(session, book)
        return services.to_book_read(session, created_book)


@app.patch("/books/{book_id}")
def update_book(session: SessionDep, book_id: int, book: BookUpdate) -> Book:
    return services.update_book(session, book_id, book)

@mcp_app.tool()
def update_book_tool(name: str, author_name: str, book: BookUpdate) -> BookRead:
    """Update an existing book, identified by its name and its author's name."""
    with Session(engine) as session:
        existing_book = services.get_book_by_name(session, name, author_name)
        if book.author_id is None:
            book.author_id = existing_book.author_id
        updated_book = services.update_book(session, existing_book.id, book)
        return services.to_book_read(session, updated_book)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(session: SessionDep, book_id: int) -> None:
    services.delete_book(session, book_id)

@mcp_app.tool()
def delete_book_tool(name: str, author_name: str) -> None:
    """Delete a book, identified by its name and its author's name."""
    with Session(engine) as session:
        existing_book = services.get_book_by_name(session, name, author_name)
        services.delete_book(session, existing_book.id)


@app.get("/authors")
def list_authors(
    session: SessionDep,
    query= QueryBuilder(Author),
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,) -> list[Author]:
    return services.list_authors(session, query, limit, offset)

@mcp_app.tool()
def list_authors_tool(
    name: str | None = None,
    page: Annotated[int, Field(ge=1)] = 1,
    page_size: Annotated[int, Field(ge=1, le=100)] = 20,
) -> Page[Author]:
    """List authors, optionally filtered. `name` is an optional partial, case-insensitive match.
    The result is paginated: `items` holds the authors on the requested `page` (1-based),
    `count` is how many items this page holds, `total` is how many authors match the filter
    overall, and `total_pages` is the number of pages at this `page_size`. If `page` is past
    `total_pages`, `items` is empty; request the next page by increasing `page`."""
    with Session(engine) as session:
        query = services.build_authors_query(name)
        return services.paginate(session, Author, query, page, page_size, lambda author: author)


@app.get("/authors/{author_id}")
def get_author(session: SessionDep, author_id: int) -> Author:
    return services.get_author(session, author_id)


@app.post("/authors", status_code=201)
def create_author(session: SessionDep, author: AuthorCreateUpdate) -> Author:
    return services.create_author(session, author)

@mcp_app.tool()
def create_author_tool(name: str) -> Author:
    """Create a new author."""
    with Session(engine) as session:
        return services.create_author(session, AuthorCreateUpdate(name=name))


@app.patch("/authors/{author_id}")
def update_author(session: SessionDep, author_id: int, author: AuthorCreateUpdate) -> Author:
    return services.update_author(session, author_id, author)

@mcp_app.tool()
def update_author_tool(name: str, new_name: str) -> Author:
    """Rename an existing author, identified by their current name."""
    with Session(engine) as session:
        existing_author = services.get_author_by_name(session, name)
        return services.update_author(session, existing_author.id, AuthorCreateUpdate(name=new_name))


@app.delete("/authors/{author_id}", status_code=204)
def delete_author(session: SessionDep, author_id: int) -> None:
    services.delete_author(session, author_id)

@mcp_app.tool()
def delete_author_tool(name: str) -> None:
    """Delete an author by name."""
    with Session(engine) as session:
        existing_author = services.get_author_by_name(session, name)
        services.delete_author(session, existing_author.id)
