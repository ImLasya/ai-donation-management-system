"""ensure_ngo_registration_unique

Revision ID: ceaa8c89e89b
Revises: f7d968b5674c
Create Date: 2026-07-07 17:53:03.446001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ceaa8c89e89b'
down_revision: Union[str, Sequence[str], None] = 'f7d968b5674c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    
    # 1. Safely resolve any case-insensitive or space-insensitive duplicate registration numbers
    # without deleting records or breaking foreign keys.
    bind.execute(sa.text("""
        UPDATE ngo_profiles
        SET registration_number = registration_number || '-dup-' || id
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM ngo_profiles
            GROUP BY LOWER(TRIM(registration_number))
        );
    """))

    # 2. Check if the UNIQUE constraint already exists on registration_number
    result = bind.execute(sa.text("""
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'ngo_profiles_registration_number_key'
    """)).fetchone()

    if not result:
        op.create_unique_constraint(
            'ngo_profiles_registration_number_key', 
            'ngo_profiles', 
            ['registration_number']
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    result = bind.execute(sa.text("""
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'ngo_profiles_registration_number_key'
    """)).fetchone()

    if result:
        op.drop_constraint('ngo_profiles_registration_number_key', 'ngo_profiles', type_='unique')
