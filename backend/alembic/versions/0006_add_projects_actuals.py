"""Add projects table, is_actuals flag, and project_id FK"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels = None
depends_on = None

_DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # 1. Projects table
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Seed default project
    op.execute(
        f"INSERT INTO projects (id, name, description) "
        f"VALUES ('{_DEFAULT_PROJECT_ID}', 'Default', 'Default project')"
    )

    # 3. Add project_id to datasets (nullable FK)
    op.add_column(
        "datasets",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_datasets_project",
        "datasets",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        f"UPDATE datasets SET project_id = '{_DEFAULT_PROJECT_ID}'"
    )

    # 4. Add is_actuals flag to datasets
    op.add_column(
        "datasets",
        sa.Column(
            "is_actuals",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    # 5. Add project_id to training_runs (nullable FK)
    op.add_column(
        "training_runs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_training_runs_project",
        "training_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        f"UPDATE training_runs SET project_id = '{_DEFAULT_PROJECT_ID}'"
    )


def downgrade() -> None:
    op.drop_constraint("fk_training_runs_project", "training_runs", type_="foreignkey")
    op.drop_column("training_runs", "project_id")
    op.drop_column("datasets", "is_actuals")
    op.drop_constraint("fk_datasets_project", "datasets", type_="foreignkey")
    op.drop_column("datasets", "project_id")
    op.drop_table("projects")
