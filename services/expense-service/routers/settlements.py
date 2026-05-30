import logging
from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import get_current_user_id
from models import Settlement, GroupMember, Expense, ExpenseSplit, MemberRole
from schemas import SettlementCreate, SettlementResponse, UserInfo
from utils.auth_client import get_users_batch

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[SettlementResponse])
async def list_settlements(
    group_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """List settlements, optionally filtered by group."""
    uid = UUID(current_user_id)

    query = (
        select(Settlement)
        .order_by(Settlement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

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
        query = query.where(Settlement.group_id == group_id)
    else:
        member_groups = await db.execute(
            select(GroupMember.group_id).where(GroupMember.user_id == uid)
        )
        group_ids = [row[0] for row in member_groups.fetchall()]
        query = query.where(Settlement.group_id.in_(group_ids))

    result = await db.execute(query)
    settlements = result.scalars().all()
    return await _build_settlement_responses(settlements)


@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement(
    payload: SettlementCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Record a settlement payment and mark outstanding expense splits as settled
    between the two parties (in chronological order) up to the settlement amount.
    """
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

    # Only allow recording on one's own behalf unless the current user is an owner
    if payload.paid_by != uid:
        owner_check = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == payload.group_id,
                GroupMember.user_id == uid,
                GroupMember.role == MemberRole.owner,
            )
        )
        if not owner_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only record settlements on your own behalf",
            )

    settlement = Settlement(
        group_id=payload.group_id,
        paid_by=payload.paid_by,
        paid_to=payload.paid_to,
        amount=payload.amount,
        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(settlement)
    await db.flush()

    # Mark unsettled splits as settled for the debtor (paid_by) toward the creditor (paid_to)
    # Only match splits whose expense currency matches the settlement currency.
    unsettled_result = await db.execute(
        select(ExpenseSplit)
        .join(Expense, ExpenseSplit.expense_id == Expense.id)
        .where(
            Expense.group_id == payload.group_id,
            Expense.paid_by == payload.paid_to,
            Expense.currency == payload.currency,
            ExpenseSplit.user_id == payload.paid_by,
            ExpenseSplit.owed_amount > 0,
            ExpenseSplit.settled_at == None,  # noqa: E711
        )
        .order_by(Expense.date.asc(), Expense.created_at.asc())
    )
    unsettled_splits = unsettled_result.scalars().all()

    remaining = payload.amount
    now = datetime.now(UTC)
    for split in unsettled_splits:
        if remaining <= Decimal("0.00"):
            break
        if split.owed_amount <= remaining:
            remaining -= split.owed_amount
            split.settled_at = now
        else:
            split.owed_amount -= remaining
            remaining = Decimal("0.00")

    await db.commit()
    await db.refresh(settlement)

    responses = await _build_settlement_responses([settlement])
    return responses[0]


@router.get("/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(
    settlement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get a single settlement by ID."""
    uid = UUID(current_user_id)
    result = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found"
        )

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == settlement.group_id, GroupMember.user_id == uid
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    responses = await _build_settlement_responses([settlement])
    return responses[0]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _build_settlement_responses(
    settlements: list[Settlement],
) -> list[SettlementResponse]:
    user_ids: set[UUID] = set()
    for s in settlements:
        user_ids.add(s.paid_by)
        user_ids.add(s.paid_to)

    users_map = await get_users_batch(list(user_ids))

    return [
        SettlementResponse(
            id=s.id,
            group_id=s.group_id,
            paid_by=s.paid_by,
            paid_to=s.paid_to,
            amount=s.amount,
            currency=s.currency,
            notes=s.notes,
            created_at=s.created_at,
            paid_by_user=UserInfo(**users_map[str(s.paid_by)])
            if str(s.paid_by) in users_map
            else None,
            paid_to_user=UserInfo(**users_map[str(s.paid_to)])
            if str(s.paid_to) in users_map
            else None,
        )
        for s in settlements
    ]
