"""add banner position

Revision ID: fb27b3f398a4
Revises: b565ddcb2ce1
Create Date: 2026-08-12 18:44:13.827443
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fb27b3f398a4"
down_revision = "b565ddcb2ce1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "banner",
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default="1"
        )
    )

    op.alter_column(
        "banner",
        "position",
        server_default=None
    )


def downgrade():
    op.drop_column("banner", "position")