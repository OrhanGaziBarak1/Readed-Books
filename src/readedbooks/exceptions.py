from sqlalchemy.exc import IntegrityError


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


CONSTRAINT_MESSAGES = {
    "uq_author_name": "An author with this name already exists.",
    "uq_book_name_author_id": "This author already has a book with that name.",
    "fk_book_author_id": "Cannot delete this author because they still have books.",
}


def integrity_error_message(exc: IntegrityError) -> str:
    constraint_name: str | None = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name is None:
        return "This operation violates a database constraint."
    return CONSTRAINT_MESSAGES.get(constraint_name, "This operation violates a database constraint.")
