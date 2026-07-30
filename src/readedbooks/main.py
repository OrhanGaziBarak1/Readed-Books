from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from readedbooks.db import get_session
from readedbooks.models import (
    Author,
    AuthorCreateUpdate,
    Book,
    BookCreate,
    BookUpdate,
)

app = FastAPI()

UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_author_name": "An author with this name already exists.",
    "uq_book_name_author_id": "This author already has a book with that name.",
}


@app.exception_handler(IntegrityError)
def handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
    constraint_name: str | None = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    message = (
        UNIQUE_CONSTRAINT_MESSAGES[constraint_name]
        if constraint_name in UNIQUE_CONSTRAINT_MESSAGES
        else "This operation violates a database constraint."
    )
    return JSONResponse(status_code=409, content={"detail": message})

SessionDep = Annotated[Session, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]


@app.get("/books")
def list_books(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0) -> list[Book]:
    return list(session.exec(select(Book).offset(offset).limit(limit)).all())


@app.get("/books/{book_id}")
def get_book(session: SessionDep, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books", status_code=201)
def create_book(session: SessionDep, book: BookCreate) -> Book:
    if book.author_id is not None and session.get(Author, book.author_id) is None:
        raise HTTPException(status_code=404, detail=f"Author {book.author_id} not found")
    db_book = Book.model_validate(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


@app.patch("/books/{book_id}")
def update_book(session: SessionDep, book_id: int, book: BookUpdate) -> Book:
    db_book = session.get(Book, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.author_id is not None and session.get(Author, book.author_id) is None:
        raise HTTPException(status_code=404, detail=f"Author {book.author_id} not found")
    for field, value in book.model_dump(exclude_unset=True).items():
        setattr(db_book, field, value)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(session: SessionDep, book_id: int) -> None:
    db_book = session.get(Book, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    session.delete(db_book)
    session.commit()


@app.get("/authors")
def list_authors(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0) -> list[Author]:
    return list(session.exec(select(Author).offset(offset).limit(limit)).all())


@app.get("/authors/{author_id}")
def get_author(session: SessionDep, author_id: int) -> Author:
    author = session.get(Author, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return author


@app.post("/authors", status_code=201)
def create_author(session: SessionDep, author: AuthorCreateUpdate) -> Author:
    db_author = Author.model_validate(author)
    session.add(db_author)
    session.commit()
    session.refresh(db_author)
    return db_author


@app.patch("/authors/{author_id}")
def update_author(session: SessionDep, author_id: int, author: AuthorCreateUpdate) -> Author:
    db_author = session.get(Author, author_id)
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    for field, value in author.model_dump(exclude_unset=True).items():
        setattr(db_author, field, value)
    session.add(db_author)
    session.commit()
    session.refresh(db_author)
    return db_author


@app.delete("/authors/{author_id}", status_code=204)
def delete_author(session: SessionDep, author_id: int) -> None:
    db_author = session.get(Author, author_id)
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    session.delete(db_author)
    session.commit()
