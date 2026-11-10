"""accounts and teams: email verification, TOTP two-factor, workspaces, invites, shared sessions

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('totp_secret', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('totp_last_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('recovery_hashes', sa.JSON(), nullable=False, server_default='[]'))
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('created_by', sa.String(32), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'workspace_members',
        sa.Column('workspace_id', sa.String(32), sa.ForeignKey('workspaces.id'), primary_key=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), primary_key=True, index=True),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'workspace_invites',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('workspace_id', sa.String(32), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_by', sa.String(32), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table('nav_sessions') as batch:
        batch.add_column(sa.Column('workspace_id', sa.String(32), nullable=True))
        batch.create_foreign_key('fk_nav_sessions_workspace', 'workspaces', ['workspace_id'], ['id'])
        batch.create_index('ix_nav_sessions_workspace_id', ['workspace_id'])


def downgrade() -> None:
    with op.batch_alter_table('nav_sessions') as batch:
        batch.drop_index('ix_nav_sessions_workspace_id')
        batch.drop_constraint('fk_nav_sessions_workspace', type_='foreignkey')
        batch.drop_column('workspace_id')
    op.drop_table('workspace_invites')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    for c in ('recovery_hashes', 'totp_last_step', 'totp_enabled', 'totp_secret', 'email_verified_at'):
        op.drop_column('users', c)
