"""
recurring_worker.py
===================
Daily job that processes recurring expenses.

For every active recurring_expense whose next_due date is today or in the
past the worker:
  1. Inserts a new expense row in expenses_schema.expenses.
  2. Inserts per-member split rows in expenses_schema.expense_splits.
  3. Advances next_due by the configured frequency.

All operations for a single recurring expense are wrapped in a savepoint so
that a failure on one row does not roll back the others.
"""
import asyncio
import calendar
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from ..database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ─── helpers ────────────────────────────────────────────────────────────────

def _add_months(dt: date, months: int) -> date:
    """Add *months* to *dt*, clamping day to the last day of the target month."""
    total_months = dt.month - 1 + months
    year = dt.year + total_months // 12
    month = total_months % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def next_due_date(current: date, frequency: str) -> date:
    """Return the next due date for a given frequency string."""
    freq = frequency.lower()
    if freq == "daily":
        return current + timedelta(days=1)
    if freq == "weekly":
        return current + timedelta(weeks=1)
    if freq == "biweekly":
        return current + timedelta(weeks=2)
    if freq == "monthly":
        return _add_months(current, 1)
    if freq == "quarterly":
        return _add_months(current, 3)
    if freq == "yearly":
        return _add_months(current, 12)
    # Unknown frequency – default to monthly
    logger.warning("Unknown frequency '%s', defaulting to monthly", frequency)
    return _add_months(current, 1)


# ─── main job ───────────────────────────────────────────────────────────────

async def process_recurring_expenses() -> None:
    """
    Find all overdue recurring expenses and materialise them as real expenses.
    Designed to run daily.
    """
    today = date.today()
    logger.info("Processing recurring expenses for %s", today)
    processed = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT
                    id,
                    group_id,
                    description,
                    amount,
                    currency,
                    paid_by,
                    split_type,
                    frequency,
                    next_due
                FROM expenses_schema.recurring_expenses
                WHERE is_active = true
                  AND next_due <= :today
                ORDER BY next_due
                """
            ),
            {"today": today},
        )
        rows = result.fetchall()

        if not rows:
            logger.info("No recurring expenses due today")
            return

        logger.info("Found %d recurring expense(s) to process", len(rows))

        for row in rows:
            (
                recurring_id,
                group_id,
                description,
                amount,
                currency,
                paid_by,
                split_type,
                frequency,
                next_due,
            ) = row

            try:
                async with db.begin_nested():  # savepoint per expense
                    await _create_expense_for_recurring(
                        db=db,
                        recurring_id=recurring_id,
                        group_id=group_id,
                        description=description,
                        amount=Decimal(str(amount)),
                        currency=currency,
                        paid_by=paid_by,
                        split_type=split_type,
                        expense_date=next_due,
                    )

                    new_next_due = next_due_date(next_due, frequency)
                    await db.execute(
                        text(
                            """
                            UPDATE expenses_schema.recurring_expenses
                            SET next_due = :next_due,
                                updated_at = NOW()
                            WHERE id = :id
                            """
                        ),
                        {"next_due": new_next_due, "id": recurring_id},
                    )

                processed += 1
                logger.info(
                    "Processed recurring expense %s → next due %s",
                    recurring_id,
                    new_next_due,
                )

            except Exception as exc:
                failed += 1
                logger.error(
                    "Failed to process recurring expense %s: %s",
                    recurring_id,
                    exc,
                    exc_info=True,
                )

        await db.commit()

    logger.info(
        "Recurring expenses done: %d processed, %d failed", processed, failed
    )


async def _create_expense_for_recurring(
    *,
    db,
    recurring_id,
    group_id,
    description: str,
    amount: Decimal,
    currency: str,
    paid_by,
    split_type: str,
    expense_date: date,
) -> None:
    """Insert expense + splits rows for a single materialised recurring expense."""

    # ── 1. Fetch group members ──────────────────────────────────────────────
    members_result = await db.execute(
        text(
            """
            SELECT user_id
            FROM expenses_schema.group_members
            WHERE group_id = :gid
            """
        ),
        {"gid": group_id},
    )
    member_ids: list[uuid.UUID] = [row[0] for row in members_result.fetchall()]

    if not member_ids:
        logger.warning(
            "Recurring expense %s: group %s has no members – skipping",
            recurring_id,
            group_id,
        )
        return

    # ── 2. Compute equal split ──────────────────────────────────────────────
    n = Decimal(len(member_ids))
    per_person: Decimal = (amount / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Distribute rounding remainder to the payer's share
    remainder = amount - per_person * n

    # ── 3. Insert expense row ───────────────────────────────────────────────
    expense_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO expenses_schema.expenses
                (id, group_id, description, amount, currency,
                 paid_by, category, date, split_type,
                 is_recurring, recurring_id, created_by,
                 created_at, updated_at)
            VALUES
                (:id, :group_id, :description, :amount, :currency,
                 :paid_by, 'recurring', :date, :split_type,
                 true, :recurring_id, :created_by,
                 NOW(), NOW())
            """
        ),
        {
            "id": expense_id,
            "group_id": group_id,
            "description": description,
            "amount": amount,
            "currency": currency,
            "paid_by": paid_by,
            "date": expense_date,
            "split_type": split_type,
            "recurring_id": recurring_id,
            "created_by": paid_by,
        },
    )

    # ── 4. Insert split rows ────────────────────────────────────────────────
    for member_id in member_ids:
        split_id = uuid.uuid4()
        is_payer = str(member_id) == str(paid_by)

        # The payer absorbs the rounding remainder
        share = per_person + (remainder if is_payer else Decimal("0"))
        # Payer owes 0 to themselves
        owed = Decimal("0") if is_payer else per_person

        await db.execute(
            text(
                """
                INSERT INTO expenses_schema.expense_splits
                    (id, expense_id, user_id, share_amount, owed_amount)
                VALUES
                    (:id, :expense_id, :user_id, :share, :owed)
                """
            ),
            {
                "id": split_id,
                "expense_id": expense_id,
                "user_id": member_id,
                "share": share,
                "owed": owed,
            },
        )

    logger.debug(
        "Created expense %s with %d splits for recurring %s",
        expense_id,
        len(member_ids),
        recurring_id,
    )
