"""add tax details to orders

Revision ID: c64da553ada4
Revises: a0f67071bac8
Create Date: 2026-08-16 12:40:09.988022

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c64da553ada4'
down_revision = 'a0f67071bac8'
branch_labels = None
depends_on = None


def upgrade():

    # Add tax columns with temporary defaults
    with op.batch_alter_table('order', schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                'taxable_amount',
                sa.Float(),
                nullable=False,
                server_default='0'
            )
        )

        batch_op.add_column(
            sa.Column(
                'gst_rate',
                sa.Float(),
                nullable=False,
                server_default='0'
            )
        )

        batch_op.add_column(
            sa.Column(
                'gst_amount',
                sa.Float(),
                nullable=False,
                server_default='0'
            )
        )

        batch_op.add_column(
            sa.Column(
                'hsn_code',
                sa.String(length=20),
                nullable=True
            )
        )


def downgrade():

    with op.batch_alter_table('order', schema=None) as batch_op:

        batch_op.drop_column('hsn_code')
        batch_op.drop_column('gst_amount')
        batch_op.drop_column('gst_rate')
        batch_op.drop_column('taxable_amount')