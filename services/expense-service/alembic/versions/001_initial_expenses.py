"""Initial expenses schema and tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum type names (PostgreSQL native enum)
SPLIT_TYPE = postgresql.ENUM("equal", "exact", "percentage", name="splittype", schema="expenses_schema")
RECURRING_FREQ = postgresql.ENUM("daily", "weekly", "monthly", "yearly", name="recurringfrequency", schema="expenses_schema")
MEMBER_ROLE = postgresql.ENUM("owner", "member", name="memberrole", schema="expenses_schema")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS expenses_schema")

    # Create enum types
    SPLIT_TYPE.create(op.get_bind(), checkfirst=True)
    RECURRING_FREQ.create(op.get_bind(), checkfirst=True)
    MEMBER_ROLE.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # groups
    # ------------------------------------------------------------------
    op.create_table(
        "groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_groups_created_by",
        "groups",
        ["created_by"],
        schema="expenses_schema",
    )

    # ------------------------------------------------------------------
    # group_members
    # ------------------------------------------------------------------
    op.create_table(
        "group_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "member", name="memberrole", schema="expenses_schema"),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["expenses_schema.groups.id"],
            ondelete="CASCADE",
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_group_members_group_id",
        "group_members",
        ["group_id"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_group_members_user_id",
        "group_members",
        ["user_id"],
        schema="expenses_schema",
    )

    # ------------------------------------------------------------------
    # recurring_expenses  (defined before expenses so FK works)
    # ------------------------------------------------------------------
    op.create_table(
        "recurring_expenses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("paid_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "split_type",
            sa.Enum("equal", "exact", "percentage", name="splittype", schema="expenses_schema"),
            nullable=False,
            server_default="equal",
        ),
        sa.Column(
            "frequency",
            sa.Enum("daily", "weekly", "monthly", "yearly", name="recurringfrequency", schema="expenses_schema"),
            nullable=False,
        ),
        sa.Column("next_due", sa.Date(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["expenses_schema.groups.id"],
            ondelete="CASCADE",
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_recurring_group_id",
        "recurring_expenses",
        ["group_id"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_recurring_next_due",
        "recurring_expenses",
        ["next_due"],
        schema="expenses_schema",
    )

    # ------------------------------------------------------------------
    # expenses
    # ------------------------------------------------------------------
    op.create_table(
        "expenses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("paid_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "split_type",
            sa.Enum("equal", "exact", "percentage", name="splittype", schema="expenses_schema"),
            nullable=False,
            server_default="equal",
        ),
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("recurring_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["expenses_schema.groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recurring_id"],
            ["expenses_schema.recurring_expenses.id"],
            ondelete="SET NULL",
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_expenses_group_id",
        "expenses",
        ["group_id"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_expenses_paid_by",
        "expenses",
        ["paid_by"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_expenses_date",
        "expenses",
        ["date"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_expenses_created_by",
        "expenses",
        ["created_by"],
        schema="expenses_schema",
    )

    # ------------------------------------------------------------------
    # expense_splits
    # ------------------------------------------------------------------
    op.create_table(
        "expense_splits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("expense_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("owed_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["expense_id"],
            ["expenses_schema.expenses.id"],
            ondelete="CASCADE",
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_splits_expense_id",
        "expense_splits",
        ["expense_id"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_splits_user_id",
        "expense_splits",
        ["user_id"],
        schema="expenses_schema",
    )

    # ------------------------------------------------------------------
    # settlements
    # ------------------------------------------------------------------
    op.create_table(
        "settlements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paid_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paid_to", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["expenses_schema.groups.id"],
            ondelete="CASCADE",
        ),
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_settlements_group_id",
        "settlements",
        ["group_id"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_settlements_paid_by",
        "settlements",
        ["paid_by"],
        schema="expenses_schema",
    )
    op.create_index(
        "ix_expenses_settlements_paid_to",
        "settlements",
        ["paid_to"],
        schema="expenses_schema",
    )


def downgrade() -> None:
    op.drop_table("settlements", schema="expenses_schema")
    op.drop_table("expense_splits", schema="expenses_schema")
    op.drop_table("expenses", schema="expenses_schema")
    op.drop_table("recurring_expenses", schema="expenses_schema")
    op.drop_table("group_members", schema="expenses_schema")
    op.drop_table("groups", schema="expenses_schema")

    SPLIT_TYPE.drop(op.get_bind(), checkfirst=True)
    RECURRING_FREQ.drop(op.get_bind(), checkfirst=True)
    MEMBER_ROLE.drop(op.get_bind(), checkfirst=True)

    op.execute("DROP SCHEMA IF EXISTS expenses_schema CASCADE")
