"""rename book author_id fk to fk_book_author_id

Revision ID: 8bc54ef31940
Revises: 4fe7bc45bc57
Create Date: 2026-10-08 21:52:37.342042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bc54ef31940'
down_revision: Union[str, Sequence[str], None] = '4fe7bc45bc57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('book_author_id_fkey', 'book', type_='foreignkey')
    op.create_foreign_key('fk_book_author_id', 'book', 'author', ['author_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_book_author_id', 'book', type_='foreignkey')
    op.create_foreign_key('book_author_id_fkey', 'book', 'author', ['author_id'], ['id'])
