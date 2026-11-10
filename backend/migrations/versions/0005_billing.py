"""billing: subscriptions, orders, invoices

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('plan', sa.String(24), nullable=False),
        sa.Column('interval', sa.String(8), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'billing_orders',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('plan', sa.String(24), nullable=False),
        sa.Column('interval', sa.String(8), nullable=False),
        sa.Column('amount_paise', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('provider_ref', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_billing_orders_user_id', 'billing_orders', ['user_id'])
    op.create_index('ix_billing_orders_provider_ref', 'billing_orders', ['provider_ref'])
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('seq', sa.Integer(), nullable=False, unique=True),
        sa.Column('number', sa.String(32), nullable=False, unique=True),
        sa.Column('order_id', sa.String(32), sa.ForeignKey('billing_orders.id'), nullable=False, unique=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('description', sa.String(200), nullable=False),
        sa.Column('taxable_paise', sa.Integer(), nullable=False),
        sa.Column('gst_paise', sa.Integer(), nullable=False),
        sa.Column('total_paise', sa.Integer(), nullable=False),
        sa.Column('gst_percent', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])


def downgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('billing_orders')
    op.drop_table('subscriptions')
