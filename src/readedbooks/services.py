from sqlalchemy import Select
from sqlmodel import Session, select

from readedbooks.exceptions import NotFoundError
from readedbooks.models import (
    Author,
    AuthorCreateUpdate,
    Book,
    BookCreate,
    BookUpdate,
)


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
