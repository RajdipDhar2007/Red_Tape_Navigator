"""external provider requests and webhook de-duplication

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'external_requests',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('session_id', sa.String(32), sa.ForeignKey('nav_sessions.id'), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('external_id', sa.String(64), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('meta', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_external_requests_user_id', 'external_requests', ['user_id'])
    op.create_index('ix_external_requests_session_id', 'external_requests', ['session_id'])
    op.create_index('ix_external_requests_external_id', 'external_requests', ['external_id'])
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('webhook_events')
    op.drop_table('external_requests')
