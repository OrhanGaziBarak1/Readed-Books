import math
from typing import IO, Any, Callable

import pandas as pd
from sqlalchemy import Select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, func, select

from readedbooks.exceptions import NotFoundError
from readedbooks.models import (
    Author,
    AuthorCreateUpdate,
    Book,
    BookCreate,
    BookImportError,
    BookImportResult,
    BookRead,
    BookUpdate,
    Language,
    Page,
    Status,
    T,
)


class CsvColumns:
    NAME = "Kitap Adı"
    LENGTH = "Sayfa Sayısı"
    STATUS = "Okuma Durumu"
    LANGUAGE = "Dil"
    AUTHORS = "Yazarlar"


CSV_STATUS_MAP = {
    "Okudum": Status.READ,
    "Okumadım": Status.UNREAD,
    "Okuyorum": Status.READING,
}

CSV_LANGUAGE_MAP = {
    "Türkçe": Language.TR,
    "İngilizce": Language.EN,
}


def list_books(session: Session, query: Select, limit: int, offset: int) -> list[Book]:
    result = session.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())

def get_book(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None:
        raise NotFoundError(f"Book not found with id {book_id}")
    return book

def create_book(session: Session, book: BookCreate) -> Book:
    if book.author_id is None:
        raise NotFoundError(f"Author {book.author_id} not found")
    if session.get(Author, book.author_id) is None:
        raise NotFoundError(f"Author {book.author_id} not found")
    db_book = Book.model_validate(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

def update_book(session: Session, book_id: int, book: BookUpdate) -> Book:
    if book.author_id is None:
        raise NotFoundError(f"Author {book.author_id} not found")
    if session.get(Author, book.author_id) is None:
        raise NotFoundError(f"Author {book.author_id} not found")
    
    db_book = session.get(Book, book_id)
    if db_book is None:
        raise NotFoundError(f"Book not found with id {book_id}")
    
    for field, value in book.model_dump(exclude_unset=True).items():
        setattr(db_book, field, value)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book

def delete_book(session: Session, book_id: int) -> None:    
    db_book = session.get(Book, book_id)
    if db_book is None:
        raise NotFoundError(f"Book not found with id {book_id}")
    
    session.delete(db_book)
    session.commit()

def list_authors(session: Session, query:Select, limit: int, offset: int) -> list[Author]:
    result = session.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())

def get_author(session: Session, author_id: int) -> Author:    
    author = session.get(Author, author_id)
    if author is None:
        raise NotFoundError(f"Author not found with id {author_id}")
    
    return author

def create_author(session: Session, author: AuthorCreateUpdate) -> Author:
    db_author = Author.model_validate(author)
    session.add(db_author)
    session.commit()
    session.refresh(db_author)
    return db_author

def update_author(session: Session, author_id: int, author: AuthorCreateUpdate) -> Author:
    db_author = session.get(Author, author_id)
    if db_author is None:
        raise NotFoundError(f"Author not found with id {author_id}")
    for field, value in author.model_dump(exclude_unset=True).items():
        setattr(db_author, field, value)
    session.add(db_author)
    session.commit()
    session.refresh(db_author)
    return db_author

def delete_author(session: Session, author_id: int) -> None:
    db_author = session.get(Author, author_id)
    if db_author is None:
        raise NotFoundError(f"Author not found with id {author_id}")
    session.delete(db_author)
    session.commit()

def to_book_read(session: Session, book: Book) -> BookRead:
    author = session.get(Author, book.author_id)
    return BookRead(
        id=book.id,
        name=book.name,
        length=book.length,
        author_name=author.name if author else None,
        status=book.status,
        language=book.language,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )

def get_author_by_name(session: Session, name: str) -> Author:
    author = session.exec(select(Author).where(Author.name == name)).first()
    if author is None:
        raise NotFoundError(f"Author not found with name {name}")
    return author

def get_book_by_name(session: Session, name: str, author_name: str) -> Book:
    author = get_author_by_name(session, author_name)
    book = session.exec(
        select(Book).where(Book.name == name, Book.author_id == author.id)
    ).first()
    if book is None:
        raise NotFoundError(f"Book not found with name {name!r} for author {author_name!r}")
    return book

def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"

def build_books_query(
    name: str | None = None,
    author_name: str | None = None,
    status: Status | None = None,
    language: Language | None = None,
) -> Select:
    query = select(Book)
    if name is not None:
        query = query.where(Book.name.ilike(_contains_pattern(name), escape="\\"))
    if author_name is not None:
        query = query.join(Author, Book.author_id == Author.id).where(
            Author.name.ilike(_contains_pattern(author_name), escape="\\")
        )
    if status is not None:
        query = query.where(Book.status == status)
    if language is not None:
        query = query.where(Book.language == language)
    return query

def build_authors_query(name: str | None = None) -> Select:
    query = select(Author)
    if name is not None:
        query = query.where(Author.name.ilike(_contains_pattern(name), escape="\\"))
    return query

def count_rows(session: Session, query: Select) -> int:
    return session.exec(select(func.count()).select_from(query.subquery())).one()

def paginate(
    session: Session,
    model: type[SQLModel],
    query: Select,
    page: int,
    page_size: int,
    to_item: Callable[[Any], T],
) -> Page[T]:
    # Offset pagination is only stable with a deterministic order, so it is applied here
    # (by primary key) instead of being left to every caller to remember.
    ordered = query.order_by(*sa_inspect(model).primary_key)
    total = count_rows(session, query)
    rows = session.execute(ordered.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = [to_item(row) for row in rows]
    return Page(
        items=items,
        page=page,
        page_size=page_size,
        count=len(items),
        total=total,
        total_pages=math.ceil(total / page_size),
    )

def get_or_create_author(session: Session, name: str) -> Author:
    author = session.exec(select(Author).where(Author.name == name)).first()
    if author is None:
        author = Author(name=name)
        session.add(author)
        session.flush()
    return author

def import_books_from_csv(session: Session, file: IO[bytes]) -> BookImportResult:
    df = pd.read_csv(file, encoding="utf-8-sig")
    created = 0
    errors: list[BookImportError] = []

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        try:
            author = get_or_create_author(session, str(row[CsvColumns.AUTHORS]).strip())
            book = Book(
                name=str(row[CsvColumns.NAME]).strip(),
                length=int(row[CsvColumns.LENGTH]),
                author_id=author.id,
                status=CSV_STATUS_MAP[str(row[CsvColumns.STATUS]).strip()],
                language=CSV_LANGUAGE_MAP[str(row[CsvColumns.LANGUAGE]).strip()],
            )
            session.add(book)
            session.commit()
            created += 1
        except (IntegrityError, KeyError, ValueError) as exc:
            session.rollback()
            errors.append(BookImportError(row=row_number, message=str(exc)))

    return BookImportResult(created=created, skipped=len(errors), errors=errors)
