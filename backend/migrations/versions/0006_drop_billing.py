"""drop billing tables: the product is free and never charges anyone

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('billing_orders')
    op.drop_table('subscriptions')


def downgrade() -> None:
    # Recreates the empty tables of 0005 so the chain can be walked back; no data is restored.
    op.create_table(
        'subscriptions',
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('plan', sa.String(24), nullable=False),
        sa.Column('interval', sa.String(8), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'billing_orders',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('plan', sa.String(24), nullable=False),
        sa.Column('interval', sa.String(8), nullable=False),
        sa.Column('amount_paise', sa.Integer, nullable=False),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('provider_ref', sa.String(64), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('seq', sa.Integer, nullable=False, unique=True),
        sa.Column('number', sa.String(32), nullable=False, unique=True),
        sa.Column('order_id', sa.String(32), sa.ForeignKey('billing_orders.id'), nullable=False, unique=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('description', sa.String(200), nullable=False),
        sa.Column('taxable_paise', sa.Integer, nullable=False),
        sa.Column('gst_paise', sa.Integer, nullable=False),
        sa.Column('total_paise', sa.Integer, nullable=False),
        sa.Column('gst_percent', sa.Integer, nullable=False),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
    )
