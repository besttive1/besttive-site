"""add banner table

Revision ID: b565ddcb2ce1
Revises: e560a80a6c3b
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b565ddcb2ce1"
down_revision = "e560a80a6c3b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "banner",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("image", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade():
    op.drop_table("banner")