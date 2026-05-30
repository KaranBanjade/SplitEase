import logging
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import get_current_user_id
from models import RecurringExpense, GroupMember, MemberRole, RecurringFrequency
from schemas import (
    RecurringExpenseCreate,
    RecurringExpenseResponse,
    RecurringExpenseUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _next_due_after(current_due, frequency: RecurringFrequency):
    """Advance a due date by one frequency interval."""
    import calendar
    from datetime import date

    if frequency == RecurringFrequency.daily:
        return current_due + timedelta(days=1)
    if frequency == RecurringFrequency.weekly:
        return current_due + timedelta(weeks=1)
    if frequency == RecurringFrequency.monthly:
        month = current_due.month + 1
        year = current_due.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(current_due.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == RecurringFrequency.yearly:
        return current_due.replace(year=current_due.year + 1)
    raise ValueError(f"Unknown frequency: {frequency}")


@router.get("", response_model=list[RecurringExpenseResponse])
async def list_recurring(
    group_id: UUID | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """List recurring expense templates, optionally filtered by group."""
    uid = UUID(current_user_id)

    query = (
        select(RecurringExpense)
        .order_by(RecurringExpense.next_due.asc())
        .limit(limit)
        .offset(offset)
    )

    if active_only:
        query = query.where(RecurringExpense.is_active == True)  # noqa: E712

    if group_id:
        member_check = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == uid
            )
        )
        if not member_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this group",
            )
        query = query.where(RecurringExpense.group_id == group_id)
    else:
        member_groups = await db.execute(
            select(GroupMember.group_id).where(GroupMember.user_id == uid)
        )
        group_ids = [row[0] for row in member_groups.fetchall()]
        query = query.where(RecurringExpense.group_id.in_(group_ids))

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Create a recurring expense template."""
    uid = UUID(current_user_id)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == payload.group_id, GroupMember.user_id == uid
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group",
        )

    recurring = RecurringExpense(
        group_id=payload.group_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        paid_by=payload.paid_by,
        split_type=payload.split_type,
        frequency=payload.frequency,
        next_due=payload.next_due,
        is_active=True,
        created_by=uid,
    )
    db.add(recurring)
    await db.commit()
    await db.refresh(recurring)
    return recurring


@router.put("/{recurring_id}", response_model=RecurringExpenseResponse)
async def update_recurring(
    recurring_id: UUID,
    payload: RecurringExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update a recurring expense template."""
    uid = UUID(current_user_id)
    recurring = await _get_recurring_or_404(recurring_id, db)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == recurring.group_id, GroupMember.user_id == uid
        )
    )
    member = member_check.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if recurring.created_by != uid and member.role != MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or group owner can update a recurring expense",
        )

    if payload.description is not None:
        recurring.description = payload.description
    if payload.amount is not None:
        recurring.amount = payload.amount
    if payload.currency is not None:
        recurring.currency = payload.currency.upper()
    if payload.paid_by is not None:
        recurring.paid_by = payload.paid_by
    if payload.split_type is not None:
        recurring.split_type = payload.split_type
    if payload.frequency is not None:
        recurring.frequency = payload.frequency
    if payload.next_due is not None:
        recurring.next_due = payload.next_due
    if payload.is_active is not None:
        recurring.is_active = payload.is_active

    await db.commit()
    await db.refresh(recurring)
    return recurring


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_recurring(
    recurring_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Deactivate a recurring expense template (sets is_active=False).
    Historical expense records generated from this template are preserved.
    """
    uid = UUID(current_user_id)
    recurring = await _get_recurring_or_404(recurring_id, db)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == recurring.group_id, GroupMember.user_id == uid
        )
    )
    member = member_check.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if recurring.created_by != uid and member.role != MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or group owner can deactivate a recurring expense",
        )

    recurring.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

async def _get_recurring_or_404(recurring_id: UUID, db: AsyncSession) -> RecurringExpense:
    result = await db.execute(
        select(RecurringExpense).where(RecurringExpense.id == recurring_id)
    )
    recurring = result.scalar_one_or_none()
    if not recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense not found",
        )
    return recurring
