"""Add customer-facing tracking IDs to orders.

Revision ID: a91c2d7e4f10
Revises: fb27b3f398a4
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "a91c2d7e4f10"
down_revision = "fb27b3f398a4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("order", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tracking_id", sa.String(length=30), nullable=True)
        )
        batch_op.create_index(
            "ix_order_tracking_id", ["tracking_id"], unique=True
        )


def downgrade():
    with op.batch_alter_table("order", schema=None) as batch_op:
        batch_op.drop_index("ix_order_tracking_id")
        batch_op.drop_column("tracking_id")
