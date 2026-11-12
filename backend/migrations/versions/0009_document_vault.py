"""add documents table for user document vault

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.String(length=32), nullable=True),
        sa.Column('session_id', sa.String(length=32), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_object_key', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=32), server_default='general', nullable=False),
        sa.Column('scan_status', sa.String(length=32), server_default='disabled', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['nav_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_documents_user_id', 'documents', ['user_id'], unique=False)
    op.create_index('ix_documents_workspace_id', 'documents', ['workspace_id'], unique=False)
    op.create_index('ix_documents_session_id', 'documents', ['session_id'], unique=False)
    op.create_index('ix_documents_stored_object_key', 'documents', ['stored_object_key'], unique=True)
    op.create_index('ix_documents_checksum', 'documents', ['checksum'], unique=False)
    op.create_index('ix_documents_created_at', 'documents', ['created_at'], unique=False)
    op.create_index('ix_documents_deleted_at', 'documents', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_deleted_at', table_name='documents')
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_index('ix_documents_checksum', table_name='documents')
    op.drop_index('ix_documents_stored_object_key', table_name='documents')
    op.drop_index('ix_documents_session_id', table_name='documents')
    op.drop_index('ix_documents_workspace_id', table_name='documents')
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_table('documents')

