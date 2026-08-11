"""Add product categories

Revision ID: e560a80a6c3b
Revises: 47e540bca9d2
Create Date: 2026-08-11 13:34:01.154842
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = 'e560a80a6c3b'
down_revision = '47e540bca9d2'
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table('product', schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                'category',
                sa.String(length=100),
                nullable=True
            )
        )

        batch_op.add_column(
            sa.Column(
                'subcategory',
                sa.String(length=100),
                nullable=True
            )
        )


def downgrade():

    with op.batch_alter_table('product', schema=None) as batch_op:

        batch_op.drop_column('subcategory')
        batch_op.drop_column('category')