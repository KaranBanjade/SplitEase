import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user_id
from models import Group, GroupMember, MemberRole, Expense, ExpenseSplit, Settlement
from schemas import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberResponse,
    UserInfo,
    BalanceResponse,
    SimplifiedDebtResponse,
)
from utils.auth_client import get_users_batch, get_user_by_email
from utils.debt_simplification import calculate_group_balances, simplify_debts

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_group_or_404(group_id: UUID, db: AsyncSession) -> Group:
    result = await db.execute(
        select(Group)
        .where(Group.id == group_id)
        .options(selectinload(Group.members))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


async def _require_membership(group: Group, user_id: str) -> GroupMember:
    uid = UUID(user_id)
    member = next((m for m in group.members if m.user_id == uid), None)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group"
        )
    return member


async def _require_owner(group: Group, user_id: str) -> GroupMember:
    member = await _require_membership(group, user_id)
    if member.role != MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owners can perform this action",
        )
    return member


async def _enrich_members(members: list[GroupMember]) -> list[GroupMemberResponse]:
    """Fetch user info for all members in one batch call."""
    user_ids = [m.user_id for m in members]
    users_map = await get_users_batch(user_ids)

    result = []
    for m in members:
        user_dict = users_map.get(str(m.user_id))
        user_info = UserInfo(**user_dict) if user_dict else None
        result.append(
            GroupMemberResponse(
                id=m.id,
                group_id=m.group_id,
                user_id=m.user_id,
                role=m.role,
                joined_at=m.joined_at,
                user=user_info,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[GroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """List all groups where the current user is a member."""
    uid = UUID(current_user_id)
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == uid)
        .options(selectinload(Group.members))
        .order_by(Group.created_at.desc())
    )
    groups = result.scalars().all()

    responses = []
    for group in groups:
        enriched = await _enrich_members(list(group.members))
        responses.append(
            GroupResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                currency=group.currency,
                created_by=group.created_by,
                created_at=group.created_at,
                updated_at=group.updated_at,
                members=enriched,
            )
        )
    return responses


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Create a new group and add the creator as owner."""
    uid = UUID(current_user_id)

    group = Group(
        name=payload.name,
        description=payload.description,
        currency=payload.currency,
        created_by=uid,
    )
    db.add(group)
    await db.flush()

    owner_member = GroupMember(
        group_id=group.id,
        user_id=uid,
        role=MemberRole.owner,
    )
    db.add(owner_member)
    await db.commit()
    await db.refresh(group)

    result = await db.execute(
        select(Group)
        .where(Group.id == group.id)
        .options(selectinload(Group.members))
    )
    group = result.scalar_one()
    enriched = await _enrich_members(list(group.members))

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        currency=group.currency,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=enriched,
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get group details with member info fetched from auth service."""
    group = await _get_group_or_404(group_id, db)
    await _require_membership(group, current_user_id)
    enriched = await _enrich_members(list(group.members))

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        currency=group.currency,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=enriched,
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update group metadata. Owner only."""
    group = await _get_group_or_404(group_id, db)
    await _require_owner(group, current_user_id)

    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    if payload.currency is not None:
        group.currency = payload.currency

    await db.commit()
    await db.refresh(group)

    result = await db.execute(
        select(Group)
        .where(Group.id == group.id)
        .options(selectinload(Group.members))
    )
    group = result.scalar_one()
    enriched = await _enrich_members(list(group.members))

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        currency=group.currency,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=enriched,
    )


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member_by_email(
    group_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Invite a user to the group by email. Owner only.
    Looks up the user via the auth service.
    """
    group = await _get_group_or_404(group_id, db)
    await _require_owner(group, current_user_id)

    email: str | None = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="email field is required",
        )

    user_data = await get_user_by_email(email.lower())
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email address",
        )

    invited_uid = UUID(user_data["id"])

    already = next((m for m in group.members if m.user_id == invited_uid), None)
    if already:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this group",
        )

    new_member = GroupMember(
        group_id=group_id,
        user_id=invited_uid,
        role=MemberRole.member,
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    user_info = UserInfo(**user_data)
    return GroupMemberResponse(
        id=new_member.id,
        group_id=new_member.group_id,
        user_id=new_member.user_id,
        role=new_member.role,
        joined_at=new_member.joined_at,
        user=user_info,
    )


@router.delete(
    "/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Remove a member from the group. Owner only. Cannot remove the owner."""
    group = await _get_group_or_404(group_id, db)
    await _require_owner(group, current_user_id)

    target_member = next((m for m in group.members if m.user_id == user_id), None)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    if target_member.role == MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the group owner",
        )

    await db.delete(target_member)
    await db.commit()


@router.get("/{group_id}/balances", response_model=list[BalanceResponse])
async def get_balances(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Compute net balances for all members of the group."""
    group = await _get_group_or_404(group_id, db)
    await _require_membership(group, current_user_id)

    expenses_result = await db.execute(
        select(Expense)
        .where(Expense.group_id == group_id)
        .options(selectinload(Expense.splits))
    )
    expenses = expenses_result.scalars().all()

    settlements_result = await db.execute(
        select(Settlement).where(Settlement.group_id == group_id)
    )
    settlements_list = settlements_result.scalars().all()

    expense_tuples = [
        (e.paid_by, [(s.user_id, s.owed_amount) for s in e.splits])
        for e in expenses
    ]
    settlement_tuples = [
        (s.paid_by, s.paid_to, s.amount) for s in settlements_list
    ]

    balances = calculate_group_balances(expense_tuples, settlement_tuples)

    user_ids = list(balances.keys())
    users_map = await get_users_batch(user_ids)

    return [
        BalanceResponse(
            user_id=uid,
            amount=amount,
            user=UserInfo(**users_map[str(uid)]) if str(uid) in users_map else None,
        )
        for uid, amount in sorted(balances.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get("/{group_id}/simplified-debts", response_model=list[SimplifiedDebtResponse])
async def get_simplified_debts(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Return the minimum set of transactions to settle all debts in the group."""
    group = await _get_group_or_404(group_id, db)
    await _require_membership(group, current_user_id)

    expenses_result = await db.execute(
        select(Expense)
        .where(Expense.group_id == group_id)
        .options(selectinload(Expense.splits))
    )
    expenses = expenses_result.scalars().all()

    settlements_result = await db.execute(
        select(Settlement).where(Settlement.group_id == group_id)
    )
    settlements_list = settlements_result.scalars().all()

    expense_tuples = [
        (e.paid_by, [(s.user_id, s.owed_amount) for s in e.splits])
        for e in expenses
    ]
    settlement_tuples = [(s.paid_by, s.paid_to, s.amount) for s in settlements_list]

    balances = calculate_group_balances(expense_tuples, settlement_tuples)
    transactions = simplify_debts(balances)

    all_uids = list({uid for t in transactions for uid in (t[0], t[1])})
    users_map = await get_users_batch(all_uids)

    return [
        SimplifiedDebtResponse(
            from_user_id=debtor,
            to_user_id=creditor,
            amount=amount,
            currency=group.currency,
            from_user=UserInfo(**users_map[str(debtor)]) if str(debtor) in users_map else None,
            to_user=UserInfo(**users_map[str(creditor)]) if str(creditor) in users_map else None,
        )
        for debtor, creditor, amount in transactions
    ]
