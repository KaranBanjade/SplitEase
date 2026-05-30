import logging
from decimal import Decimal, ROUND_DOWN
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user_id
from models import Expense, ExpenseSplit, Group, GroupMember, SplitType, MemberRole
from schemas import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSplitResponse,
    ExpenseUpdate,
    PaginatedExpenseResponse,
    UserInfo,
)
from utils.auth_client import get_users_batch

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Split calculation helpers
# ---------------------------------------------------------------------------

def _calculate_splits(
    amount: Decimal,
    paid_by: UUID,
    split_type: SplitType,
    member_ids: list[UUID],
    split_inputs: list,
) -> list[dict]:
    """
    Return a list of dicts ready to be converted into ExpenseSplit rows.
    Each dict has: user_id, share_amount, owed_amount.
    """
    two_dp = Decimal("0.01")

    if split_type == SplitType.equal:
        n = len(member_ids)
        if n == 0:
            raise ValueError("No members to split among")
        base_share = (amount / n).quantize(two_dp, rounding=ROUND_DOWN)
        remainder = amount - base_share * n
        splits = []
        for i, uid in enumerate(member_ids):
            share = base_share + (remainder if i == 0 else Decimal("0.00"))
            share = share.quantize(two_dp)
            splits.append(
                {
                    "user_id": uid,
                    "share_amount": share,
                    "owed_amount": Decimal("0.00") if uid == paid_by else share,
                }
            )
        return splits

    if split_type == SplitType.exact:
        if not split_inputs:
            raise ValueError("split_inputs required for exact split")
        total = sum(s.amount for s in split_inputs if s.amount is not None)
        if abs(total - amount) > Decimal("0.02"):
            raise ValueError(
                f"Exact split amounts ({total}) do not sum to expense amount ({amount})"
            )
        splits = []
        for s in split_inputs:
            share = (s.amount or Decimal("0.00")).quantize(two_dp)
            splits.append(
                {
                    "user_id": s.user_id,
                    "share_amount": share,
                    "owed_amount": Decimal("0.00") if s.user_id == paid_by else share,
                }
            )
        return splits

    if split_type == SplitType.percentage:
        if not split_inputs:
            raise ValueError("split_inputs required for percentage split")
        total_pct = sum(s.percentage for s in split_inputs if s.percentage is not None)
        if abs(total_pct - Decimal("100")) > Decimal("0.01"):
            raise ValueError(f"Percentages must sum to 100 (got {total_pct})")
        computed = []
        for s in split_inputs:
            share = ((s.percentage or Decimal("0")) / 100 * amount).quantize(
                two_dp, rounding=ROUND_DOWN
            )
            computed.append(share)
        diff = amount - sum(computed)
        computed[0] += diff
        splits = []
        for i, s in enumerate(split_inputs):
            share = computed[i].quantize(two_dp)
            splits.append(
                {
                    "user_id": s.user_id,
                    "share_amount": share,
                    "owed_amount": Decimal("0.00") if s.user_id == paid_by else share,
                }
            )
        return splits

    raise ValueError(f"Unknown split type: {split_type}")


async def _get_group_member_ids(group_id: UUID, db: AsyncSession) -> list[UUID]:
    result = await db.execute(
        select(GroupMember.user_id).where(GroupMember.group_id == group_id)
    )
    return [row[0] for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedExpenseResponse)
async def list_expenses(
    group_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    uid = UUID(current_user_id)

    # Build base filter condition
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
        where_clause = Expense.group_id == group_id
    else:
        member_groups = await db.execute(
            select(GroupMember.group_id).where(GroupMember.user_id == uid)
        )
        group_ids = [row[0] for row in member_groups.fetchall()]
        where_clause = Expense.group_id.in_(group_ids)

    # Count total matching rows
    count_result = await db.execute(
        select(func.count()).select_from(Expense).where(where_clause)
    )
    total = count_result.scalar_one()

    # Fetch page
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(where_clause)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    expenses = result.scalars().all()
    items = await _build_expense_responses(list(expenses))

    return PaginatedExpenseResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Create an expense and calculate splits."""
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

    if payload.split_type == SplitType.equal:
        member_ids = await _get_group_member_ids(payload.group_id, db)
    else:
        member_ids = [s.user_id for s in payload.splits]

    if not member_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No participants for expense split",
        )

    try:
        split_data = _calculate_splits(
            amount=payload.amount,
            paid_by=payload.paid_by,
            split_type=payload.split_type,
            member_ids=member_ids,
            split_inputs=payload.splits,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    expense = Expense(
        group_id=payload.group_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        paid_by=payload.paid_by,
        category=payload.category,
        date=payload.date,
        split_type=payload.split_type,
        is_recurring=payload.is_recurring,
        recurring_id=payload.recurring_id,
        created_by=uid,
    )
    db.add(expense)
    await db.flush()

    for sd in split_data:
        db.add(
            ExpenseSplit(
                expense_id=expense.id,
                user_id=sd["user_id"],
                share_amount=sd["share_amount"],
                owed_amount=sd["owed_amount"],
            )
        )

    await db.commit()

    # Publish event to Redis Stream so Notification Worker can react in real-time
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.xadd(
                "splitease:events",
                {
                    "type": "expense.created",
                    "expense_id": str(expense.id),
                    "group_id": str(expense.group_id),
                    "created_by": str(expense.created_by),
                    "amount": str(expense.amount),
                    "description": expense.description,
                },
            )
            logger.info("Published expense.created event for expense %s", expense.id)
        except Exception as exc:
            logger.warning("Failed to publish expense.created event: %s", exc)

    result = await db.execute(
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.splits))
    )
    expense = result.scalar_one()
    responses = await _build_expense_responses([expense])
    return responses[0]


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get an expense by ID."""
    uid = UUID(current_user_id)
    expense = await _get_expense_or_404(expense_id, db)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == expense.group_id, GroupMember.user_id == uid
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    responses = await _build_expense_responses([expense])
    return responses[0]


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update an expense and recalculate splits if amount/split_type changed."""
    uid = UUID(current_user_id)
    expense = await _get_expense_or_404(expense_id, db)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == expense.group_id, GroupMember.user_id == uid
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if payload.description is not None:
        expense.description = payload.description
    if payload.category is not None:
        expense.category = payload.category
    if payload.date is not None:
        expense.date = payload.date
    if payload.currency is not None:
        expense.currency = payload.currency
    if payload.paid_by is not None:
        expense.paid_by = payload.paid_by
    if payload.amount is not None:
        expense.amount = payload.amount
    if payload.split_type is not None:
        expense.split_type = payload.split_type

    recalculate = (
        payload.amount is not None
        or payload.split_type is not None
        or payload.splits is not None
    )

    if recalculate:
        new_split_type = expense.split_type
        new_paid_by = expense.paid_by

        if new_split_type == SplitType.equal:
            member_ids = await _get_group_member_ids(expense.group_id, db)
            split_inputs = []
        else:
            split_inputs = payload.splits or []
            member_ids = [s.user_id for s in split_inputs]

        if not member_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No participants for expense split",
            )

        try:
            split_data = _calculate_splits(
                amount=expense.amount,
                paid_by=new_paid_by,
                split_type=new_split_type,
                member_ids=member_ids,
                split_inputs=split_inputs,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            )

        for s in list(expense.splits):
            await db.delete(s)
        await db.flush()

        for sd in split_data:
            db.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=sd["user_id"],
                    share_amount=sd["share_amount"],
                    owed_amount=sd["owed_amount"],
                )
            )

    await db.commit()

    result = await db.execute(
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.splits))
    )
    expense = result.scalar_one()
    responses = await _build_expense_responses([expense])
    return responses[0]


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete an expense (hard delete, splits cascade)."""
    uid = UUID(current_user_id)
    expense = await _get_expense_or_404(expense_id, db)

    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == expense.group_id, GroupMember.user_id == uid
        )
    )
    member = member_check.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if expense.created_by != uid and member.role != MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the expense creator or group owner can delete this expense",
        )

    await db.delete(expense)
    await db.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_expense_or_404(expense_id: UUID, db: AsyncSession) -> Expense:
    result = await db.execute(
        select(Expense)
        .where(Expense.id == expense_id)
        .options(selectinload(Expense.splits))
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
    return expense


async def _build_expense_responses(expenses: list[Expense]) -> list[ExpenseResponse]:
    """Build ExpenseResponse objects with enriched user info."""
    user_ids: set[UUID] = set()
    for e in expenses:
        user_ids.add(e.paid_by)
        for s in e.splits:
            user_ids.add(s.user_id)

    users_map = await get_users_batch(list(user_ids))

    responses = []
    for e in expenses:
        paid_by_data = users_map.get(str(e.paid_by))
        splits = [
            ExpenseSplitResponse(
                id=s.id,
                expense_id=s.expense_id,
                user_id=s.user_id,
                share_amount=s.share_amount,
                owed_amount=s.owed_amount,
                settled_at=s.settled_at,
                user=UserInfo(**users_map[str(s.user_id)])
                if str(s.user_id) in users_map
                else None,
            )
            for s in e.splits
        ]
        responses.append(
            ExpenseResponse(
                id=e.id,
                group_id=e.group_id,
                description=e.description,
                amount=e.amount,
                currency=e.currency,
                paid_by=e.paid_by,
                category=e.category,
                date=e.date,
                split_type=e.split_type,
                is_recurring=e.is_recurring,
                recurring_id=e.recurring_id,
                created_by=e.created_by,
                created_at=e.created_at,
                updated_at=e.updated_at,
                splits=splits,
                paid_by_user=UserInfo(**paid_by_data) if paid_by_data else None,
            )
        )
    return responses
