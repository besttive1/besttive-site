"""set order product foreign key null on delete

Revision ID: fb521a37a8db
Revises: b2939134d512
Create Date: 2026-09-17 15:59:19.257893

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'fb521a37a8db'
down_revision = 'b2939134d512'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        'order_product_id_fkey',
        'order',
        type_='foreignkey'
    )

    op.create_foreign_key(
        'order_product_id_fkey',
        'order',
        'product',
        ['product_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint(
        'order_product_id_fkey',
        'order',
        type_='foreignkey'
    )

    op.create_foreign_key(
        'order_product_id_fkey',
        'order',
        'product',
        ['product_id'],
        ['id']
    )