from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User
from schemas import UserResponse, UpdateUser
from dependencies import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateUser,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's name and/or avatar URL."""
    updated = False

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name cannot be blank",
            )
        current_user.name = name
        updated = True

    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url or None
        updated = True

    if updated:
        current_user.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# Internal endpoints — service-to-service only (protect at network level)
# ---------------------------------------------------------------------------

@router.get(
    "/internal/users/{user_id}",
    response_model=UserResponse,
    include_in_schema=False,
)
async def internal_get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Look up a user by UUID. No JWT required — protect via network policy."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.get(
    "/internal/users/by-email/{email}",
    response_model=UserResponse,
    include_in_schema=False,
)
async def internal_get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Look up a user by email address. No JWT required — protect via network policy."""
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
