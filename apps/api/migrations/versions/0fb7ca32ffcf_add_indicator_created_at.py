"""Add created_at to indicators."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0fb7ca32ffcf"
down_revision: Union[str, Sequence[str], None] = "0003_relationship_case_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column temporarily as nullable so existing rows remain valid.
    with op.batch_alter_table("indicators") as batch_op:
        batch_op.add_column(
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Preserve existing records by using their first_seen timestamp.
    op.execute(
        "UPDATE indicators SET created_at = first_seen WHERE created_at IS NULL"
    )

    # Make the column required, matching the SQLAlchemy model.
    with op.batch_alter_table("indicators") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("indicators") as batch_op:
        batch_op.drop_column("created_at")