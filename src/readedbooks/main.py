from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from readedbooks import services
from readedbooks.db import get_session
from readedbooks.exceptions import NotFoundError, integrity_error_message
from readedbooks.models import (
    Author,
    AuthorCreateUpdate,
    Book,
    BookCreate,
    BookImportResult,
    BookUpdate,
)
from fastapi_querybuilder import QueryBuilder

app = FastAPI()


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


@app.post("/books/import")
def import_books(session: SessionDep, file: UploadFile) -> BookImportResult:
    return services.import_books_from_csv(session, file.file)


@app.get("/books/{book_id}")
def get_book(session: SessionDep, book_id: int) -> Book:
    return services.get_book(session, book_id)


@app.post("/books", status_code=201)
def create_book(session: SessionDep, book: BookCreate) -> Book:
    return services.create_book(session, book)


@app.patch("/books/{book_id}")
def update_book(session: SessionDep, book_id: int, book: BookUpdate) -> Book:
    return services.update_book(session, book_id, book)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(session: SessionDep, book_id: int) -> None:
    services.delete_book(session, book_id)


@app.get("/authors")
def list_authors(
    session: SessionDep,
    query= QueryBuilder(Author),
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,) -> list[Author]:
    return services.list_authors(session, query, limit, offset)


@app.get("/authors/{author_id}")
def get_author(session: SessionDep, author_id: int) -> Author:
    return services.get_author(session, author_id)


@app.post("/authors", status_code=201)
def create_author(session: SessionDep, author: AuthorCreateUpdate) -> Author:
    return services.create_author(session, author)


@app.patch("/authors/{author_id}")
def update_author(session: SessionDep, author_id: int, author: AuthorCreateUpdate) -> Author:
    return services.update_author(session, author_id, author)


@app.delete("/authors/{author_id}", status_code=204)
def delete_author(session: SessionDep, author_id: int) -> None:
    services.delete_author(session, author_id)
