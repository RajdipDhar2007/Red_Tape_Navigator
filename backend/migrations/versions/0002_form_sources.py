"""official form sources

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('form_sources',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('form_id', sa.String(length=64), nullable=False),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('compatible', sa.Boolean(), nullable=False),
    sa.Column('compat', sa.JSON(), nullable=False),
    sa.Column('pdf', sa.LargeBinary(), nullable=False),
    sa.Column('decided_by', sa.String(length=32), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_form_sources_form_id'), 'form_sources', ['form_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_form_sources_form_id'), table_name='form_sources')
    op.drop_table('form_sources')
