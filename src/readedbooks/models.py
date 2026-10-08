from pydantic import field_serializer
from sqlmodel import Field, SQLModel, UniqueConstraint
from sqlalchemy import Column, ForeignKey, Integer
from enum import Enum
from datetime import datetime, timezone

class Language(str, Enum):
    TR = 'Turkish'
    EN = 'English'

class Status(str, Enum):
    READ = 'read'
    UNREAD = 'unread'
    READING = 'reading'

class Author(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", name="uq_author_name"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str

class AuthorCreateUpdate(SQLModel):
    name: str

def _serialize_datetime_as_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

class Book(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", "author_id", name="uq_book_name_author_id"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str
    length: int
    author_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("author.id", name="fk_book_author_id"), nullable=True),
    )
    status: Status
    language: Language
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    @field_serializer("created_at", "updated_at")
    def _serialize_as_utc(self, value: datetime | None) -> str | None:
        return _serialize_datetime_as_utc(value)

class BookRead(SQLModel):
    id: int | None
    name: str
    length: int
    author_name: str | None
    status: Status
    language: Language
    created_at: datetime | None
    updated_at: datetime | None

    @field_serializer("created_at", "updated_at")
    def _serialize_as_utc(self, value: datetime | None) -> str | None:
        return _serialize_datetime_as_utc(value)

class BookCreate(SQLModel):
    name: str
    length: int
    author_id: int | None = None
    status: Status
    language: Language

class BookUpdate(SQLModel):
    name: str | None = None
    length: int | None = None
    author_id: int | None = None
    status: Status | None = None
    language: Language | None = None

class BookImportError(SQLModel):
    row: int
    message: str

class BookImportResult(SQLModel):
    created: int
    skipped: int
    errors: list[BookImportError]