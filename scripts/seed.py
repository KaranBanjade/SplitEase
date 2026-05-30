#!/usr/bin/env python3
"""
SplitEase Database Seed Script
================================
Creates test users, groups, expenses, and a settlement so you can
immediately explore the app after running `make dev-setup`.

Usage:
    DATABASE_URL=postgresql+asyncpg://splitease:password@localhost:5432/splitease \
        python scripts/seed.py

Test accounts created:
    alice@test.com   / password123
    bob@test.com     / password123
    charlie@test.com / password123
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

try:
    import asyncpg
    from passlib.context import CryptContext
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install asyncpg passlib[bcrypt]")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://splitease:password@localhost:5432/splitease",
)
# asyncpg uses postgresql:// not postgresql+asyncpg://
DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def table_exists(conn, schema: str, table: str) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = $1 AND table_name = $2
        """,
        schema,
        table,
    )
    return row is not None


async def check_tables(conn):
    required = [
        ("auth_schema", "users"),
        ("expenses_schema", "groups"),
        ("expenses_schema", "group_members"),
        ("expenses_schema", "expenses"),
        ("expenses_schema", "expense_splits"),
        ("expenses_schema", "settlements"),
    ]
    missing = []
    for schema, table in required:
        if not await table_exists(conn, schema, table):
            missing.append(f"{schema}.{table}")
    if missing:
        print("ERROR: The following tables are missing. Run migrations first:")
        print("  make migrate")
        for t in missing:
            print(f"    - {t}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def clear_existing(conn):
    """Remove any previously seeded test data (idempotent re-runs)."""
    print("  Clearing existing seed data...")
    test_emails = ("alice@test.com", "bob@test.com", "charlie@test.com")

    # Delete in dependency order
    await conn.execute(
        """
        DELETE FROM expenses_schema.settlements
        WHERE payer_id IN (
            SELECT id FROM auth_schema.users WHERE email = ANY($1::text[])
        )
        """,
        list(test_emails),
    )
    await conn.execute(
        """
        DELETE FROM expenses_schema.expense_splits
        WHERE user_id IN (
            SELECT id FROM auth_schema.users WHERE email = ANY($1::text[])
        )
        """,
        list(test_emails),
    )
    await conn.execute(
        """
        DELETE FROM expenses_schema.expenses
        WHERE paid_by IN (
            SELECT id FROM auth_schema.users WHERE email = ANY($1::text[])
        )
        """,
        list(test_emails),
    )
    await conn.execute(
        """
        DELETE FROM expenses_schema.group_members
        WHERE user_id IN (
            SELECT id FROM auth_schema.users WHERE email = ANY($1::text[])
        )
        """,
        list(test_emails),
    )
    await conn.execute(
        """
        DELETE FROM expenses_schema.groups
        WHERE created_by IN (
            SELECT id FROM auth_schema.users WHERE email = ANY($1::text[])
        )
        """,
        list(test_emails),
    )
    await conn.execute(
        "DELETE FROM auth_schema.users WHERE email = ANY($1::text[])",
        list(test_emails),
    )


async def create_users(conn) -> dict:
    """Create 3 test users. Returns {email: id} mapping."""
    print("  Creating users...")
    users_data = [
        {
            "email": "alice@test.com",
            "full_name": "Alice Johnson",
            "password": "password123",
        },
        {
            "email": "bob@test.com",
            "full_name": "Bob Smith",
            "password": "password123",
        },
        {
            "email": "charlie@test.com",
            "full_name": "Charlie Davis",
            "password": "password123",
        },
    ]

    user_ids = {}
    for u in users_data:
        uid = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO auth_schema.users
                (id, email, full_name, hashed_password, is_active, is_verified, created_at, updated_at)
            VALUES ($1, $2, $3, $4, TRUE, TRUE, $5, $5)
            """,
            uid,
            u["email"],
            u["full_name"],
            hash_password(u["password"]),
            now_utc(),
        )
        user_ids[u["email"]] = uid
        print(f"    Created user: {u['full_name']} <{u['email']}>")

    return user_ids


async def create_groups(conn, user_ids: dict) -> dict:
    """Create 2 groups. Returns {name: id} mapping."""
    print("  Creating groups...")
    alice = user_ids["alice@test.com"]
    bob = user_ids["bob@test.com"]
    charlie = user_ids["charlie@test.com"]

    groups_data = [
        {
            "name": "Apartment",
            "description": "Shared apartment expenses",
            "members": [alice, bob, charlie],
            "created_by": alice,
        },
        {
            "name": "Road Trip",
            "description": "Summer road trip to the coast",
            "members": [alice, bob],
            "created_by": alice,
        },
    ]

    group_ids = {}
    for g in groups_data:
        gid = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO expenses_schema.groups
                (id, name, description, created_by, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $5)
            """,
            gid,
            g["name"],
            g["description"],
            g["created_by"],
            now_utc(),
        )
        for member_id in g["members"]:
            await conn.execute(
                """
                INSERT INTO expenses_schema.group_members
                    (id, group_id, user_id, joined_at, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                """,
                str(uuid.uuid4()),
                gid,
                member_id,
                now_utc(),
            )
        group_ids[g["name"]] = gid
        print(f"    Created group: {g['name']} ({len(g['members'])} members)")

    return group_ids


async def create_expenses(conn, user_ids: dict, group_ids: dict):
    """Create 6 sample expenses covering equal, exact, and percentage splits."""
    print("  Creating expenses...")

    alice = user_ids["alice@test.com"]
    bob = user_ids["bob@test.com"]
    charlie = user_ids["charlie@test.com"]
    apartment_id = group_ids["Apartment"]
    road_trip_id = group_ids["Road Trip"]

    expenses = [
        # ---- Apartment group (3-way equal split) ----
        {
            "id": str(uuid.uuid4()),
            "group_id": apartment_id,
            "title": "Monthly Groceries",
            "amount": Decimal("120.00"),
            "currency": "USD",
            "paid_by": alice,
            "split_type": "equal",
            "date": now_utc() - timedelta(days=15),
            "splits": [
                {"user_id": alice, "amount": Decimal("40.00"), "percentage": None},
                {"user_id": bob, "amount": Decimal("40.00"), "percentage": None},
                {"user_id": charlie, "amount": Decimal("40.00"), "percentage": None},
            ],
        },
        {
            "id": str(uuid.uuid4()),
            "group_id": apartment_id,
            "title": "Electricity Bill",
            "amount": Decimal("90.00"),
            "currency": "USD",
            "paid_by": bob,
            "split_type": "equal",
            "date": now_utc() - timedelta(days=10),
            "splits": [
                {"user_id": alice, "amount": Decimal("30.00"), "percentage": None},
                {"user_id": bob, "amount": Decimal("30.00"), "percentage": None},
                {"user_id": charlie, "amount": Decimal("30.00"), "percentage": None},
            ],
        },
        {
            "id": str(uuid.uuid4()),
            "group_id": apartment_id,
            "title": "Internet Subscription",
            "amount": Decimal("60.00"),
            "currency": "USD",
            "paid_by": charlie,
            "split_type": "equal",
            "date": now_utc() - timedelta(days=5),
            "splits": [
                {"user_id": alice, "amount": Decimal("20.00"), "percentage": None},
                {"user_id": bob, "amount": Decimal("20.00"), "percentage": None},
                {"user_id": charlie, "amount": Decimal("20.00"), "percentage": None},
            ],
        },
        # ---- Apartment group (exact split – rent is not equal) ----
        {
            "id": str(uuid.uuid4()),
            "group_id": apartment_id,
            "title": "Rent – October",
            "amount": Decimal("1800.00"),
            "currency": "USD",
            "paid_by": alice,
            "split_type": "exact",
            "date": now_utc() - timedelta(days=30),
            "splits": [
                # Alice has the master bedroom
                {"user_id": alice, "amount": Decimal("700.00"), "percentage": None},
                {"user_id": bob, "amount": Decimal("600.00"), "percentage": None},
                {"user_id": charlie, "amount": Decimal("500.00"), "percentage": None},
            ],
        },
        # ---- Road Trip group (percentage split) ----
        {
            "id": str(uuid.uuid4()),
            "group_id": road_trip_id,
            "title": "Gas & Fuel",
            "amount": Decimal("200.00"),
            "currency": "USD",
            "paid_by": alice,
            "split_type": "percentage",
            "date": now_utc() - timedelta(days=20),
            "splits": [
                # Alice drove more
                {"user_id": alice, "amount": Decimal("120.00"), "percentage": Decimal("60.00")},
                {"user_id": bob, "amount": Decimal("80.00"), "percentage": Decimal("40.00")},
            ],
        },
        # ---- Road Trip group (equal split) ----
        {
            "id": str(uuid.uuid4()),
            "group_id": road_trip_id,
            "title": "Hotel Night – Big Sur",
            "amount": Decimal("180.00"),
            "currency": "USD",
            "paid_by": bob,
            "split_type": "equal",
            "date": now_utc() - timedelta(days=19),
            "splits": [
                {"user_id": alice, "amount": Decimal("90.00"), "percentage": None},
                {"user_id": bob, "amount": Decimal("90.00"), "percentage": None},
            ],
        },
    ]

    for exp in expenses:
        await conn.execute(
            """
            INSERT INTO expenses_schema.expenses
                (id, group_id, title, amount, currency, paid_by, split_type,
                 notes, date, created_at, updated_at, is_deleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NULL, $8, $8, $8, FALSE)
            """,
            exp["id"],
            exp["group_id"],
            exp["title"],
            exp["amount"],
            exp["currency"],
            exp["paid_by"],
            exp["split_type"],
            exp["date"],
        )
        for split in exp["splits"]:
            await conn.execute(
                """
                INSERT INTO expenses_schema.expense_splits
                    (id, expense_id, user_id, amount, percentage, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                str(uuid.uuid4()),
                exp["id"],
                split["user_id"],
                split["amount"],
                split.get("percentage"),
                exp["date"],
            )
        print(f"    Created expense: {exp['title']} (${exp['amount']})")


async def create_settlement(conn, user_ids: dict, group_ids: dict):
    """Create 1 settlement to show the settle-up flow."""
    print("  Creating settlement...")
    bob = user_ids["bob@test.com"]
    alice = user_ids["alice@test.com"]
    apartment_id = group_ids["Apartment"]

    await conn.execute(
        """
        INSERT INTO expenses_schema.settlements
            (id, group_id, payer_id, payee_id, amount, currency, note, settled_at, created_at)
        VALUES ($1, $2, $3, $4, $5, 'USD', 'Paying back for groceries', $6, $6)
        """,
        str(uuid.uuid4()),
        apartment_id,
        bob,
        alice,
        Decimal("40.00"),
        now_utc() - timedelta(days=8),
    )
    print("    Created settlement: Bob paid Alice $40.00")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print(f"\nConnecting to database: {DSN.split('@')[-1]}")
    try:
        conn = await asyncpg.connect(DSN)
    except Exception as e:
        print(f"ERROR: Could not connect to database.\n  {e}")
        print("\nMake sure PostgreSQL is running and the DATABASE_URL is correct.")
        print("  make up  # to start services")
        sys.exit(1)

    try:
        print("Checking database tables...")
        await check_tables(conn)

        async with conn.transaction():
            await clear_existing(conn)
            user_ids = await create_users(conn)
            group_ids = await create_groups(conn, user_ids)
            await create_expenses(conn, user_ids, group_ids)
            await create_settlement(conn, user_ids, group_ids)

        print("\nSeed completed successfully!")
        print("\nTest accounts:")
        print("  alice@test.com   / password123")
        print("  bob@test.com     / password123")
        print("  charlie@test.com / password123")
        print("\nOpen http://localhost:3000 and log in.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
