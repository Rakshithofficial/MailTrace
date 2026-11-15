"""Store source and target cases on relationship edges."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_relationship_case_links"
down_revision: Union[str, Sequence[str], None] = "0002_email_intake_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("relationships") as batch_op:
        batch_op.add_column(
            sa.Column("source_case_id", sa.String(36), nullable=True)
        )
        batch_op.add_column(
            sa.Column("target_case_id", sa.String(36), nullable=True)
        )

        batch_op.create_foreign_key(
            "fk_relationships_source_case",
            "investigation_cases",
            ["source_case_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_relationships_target_case",
            "investigation_cases",
            ["target_case_id"],
            ["id"],
            ondelete="RESTRICT",
        )

        batch_op.create_index(
            "ix_relationships_source_case",
            ["source_case_id"],
        )
        batch_op.create_index(
            "ix_relationships_target_case",
            ["target_case_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("relationships") as batch_op:
        batch_op.drop_index("ix_relationships_target_case")
        batch_op.drop_index("ix_relationships_source_case")
        batch_op.drop_constraint(
            "fk_relationships_target_case",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_relationships_source_case",
            type_="foreignkey",
        )
        batch_op.drop_column("target_case_id")
        batch_op.drop_column("source_case_id")