"""cascade delete external_requests when a nav_session is deleted

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def _fk_name(bind) -> str:
    for fk in sa.inspect(bind).get_foreign_keys('external_requests'):
        if fk.get('referred_table') == 'nav_sessions' and fk.get('constrained_columns') == ['session_id']:
            if fk.get('name'):
                return str(fk['name'])
    return 'external_requests_session_id_fkey'


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_constraint(_fk_name(bind), 'external_requests', type_='foreignkey')
        op.create_foreign_key(
            'external_requests_session_id_fkey',
            'external_requests',
            'nav_sessions',
            ['session_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_constraint(_fk_name(bind), 'external_requests', type_='foreignkey')
        op.create_foreign_key(
            'external_requests_session_id_fkey',
            'external_requests',
            'nav_sessions',
            ['session_id'],
            ['id'],
        )

