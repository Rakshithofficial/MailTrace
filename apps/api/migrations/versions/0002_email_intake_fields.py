"""Add email intake fields."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_email_intake_fields"
down_revision: Union[str, Sequence[str], None] = "0001_database_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("emails") as batch_op:
        batch_op.add_column(
            sa.Column("cc", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("body_text", sa.Text()))
        batch_op.add_column(sa.Column("body_html", sa.Text()))
        batch_op.add_column(
            sa.Column(
                "received_headers",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "authentication_results",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column("urls", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column(
                "attachments",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )

        for column in (
            "cc",
            "received_headers",
            "authentication_results",
            "urls",
            "attachments",
        ):
            batch_op.alter_column(column, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("emails") as batch_op:
        for column in (
            "attachments",
            "urls",
            "authentication_results",
            "received_headers",
            "body_html",
            "body_text",
            "cc",
        ):
            batch_op.drop_column(column)