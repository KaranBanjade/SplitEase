"""Initial auth schema and tables

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


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS auth_schema")

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        schema="auth_schema",
    )
    op.create_index("ix_auth_users_email", "users", ["email"], unique=True, schema="auth_schema")

    # ------------------------------------------------------------------
    # refresh_tokens
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_schema.users.id"],
            ondelete="CASCADE",
        ),
        schema="auth_schema",
    )
    op.create_index(
        "ix_auth_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="auth_schema",
    )
    op.create_index(
        "ix_auth_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        schema="auth_schema",
    )

    # ------------------------------------------------------------------
    # password_resets
    # ------------------------------------------------------------------
    op.create_table(
        "password_resets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_schema.users.id"],
            ondelete="CASCADE",
        ),
        schema="auth_schema",
    )
    op.create_index(
        "ix_auth_password_resets_token_hash",
        "password_resets",
        ["token_hash"],
        unique=True,
        schema="auth_schema",
    )
    op.create_index(
        "ix_auth_password_resets_user_id",
        "password_resets",
        ["user_id"],
        schema="auth_schema",
    )

    # ------------------------------------------------------------------
    # push_subscriptions
    # ------------------------------------------------------------------
    op.create_table(
        "push_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("keys_p256dh", sa.String(500), nullable=False),
        sa.Column("keys_auth", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_schema.users.id"],
            ondelete="CASCADE",
        ),
        schema="auth_schema",
    )
    op.create_index(
        "ix_auth_push_subscriptions_user_id",
        "push_subscriptions",
        ["user_id"],
        schema="auth_schema",
    )


def downgrade() -> None:
    op.drop_table("push_subscriptions", schema="auth_schema")
    op.drop_table("password_resets", schema="auth_schema")
    op.drop_table("refresh_tokens", schema="auth_schema")
    op.drop_table("users", schema="auth_schema")
    op.execute("DROP SCHEMA IF EXISTS auth_schema CASCADE")
