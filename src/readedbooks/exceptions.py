from sqlalchemy.exc import IntegrityError


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_author_name": "An author with this name already exists.",
    "uq_book_name_author_id": "This author already has a book with that name.",
}


def integrity_error_message(exc: IntegrityError) -> str:
    constraint_name: str | None = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name is None:
        return "This operation violates a database constraint."
    return UNIQUE_CONSTRAINT_MESSAGES.get(constraint_name, "This operation violates a database constraint.")
