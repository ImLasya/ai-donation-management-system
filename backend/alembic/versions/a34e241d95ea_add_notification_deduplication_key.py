"""add_notification_deduplication_key

Revision ID: a34e241d95ea
Revises: ceaa8c89e89b
Create Date: 2026-07-08 23:40:20.609090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a34e241d95ea'
down_revision: Union[str, Sequence[str], None] = 'ceaa8c89e89b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notifications', sa.Column('deduplication_key', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_notification_deduplication_key', 'notifications', ['deduplication_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_notification_deduplication_key', 'notifications', type_='unique')
    op.drop_column('notifications', 'deduplication_key')
