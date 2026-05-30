import logging
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models import User, RefreshToken, PasswordReset, PushSubscription
from schemas import (
    UserCreate,
    UserLogin,
    AuthResponse,
    UserResponse,
    RefreshRequest,
    AccessTokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    LogoutRequest,
    PushSubscriptionCreate,
)
from utils.jwt import create_access_token, create_refresh_token, hash_token
from utils.password import hash_password, verify_password
from utils.email import send_password_reset_email
from dependencies import get_current_user
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user and return access + refresh tokens."""
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email.lower(),
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    raw_token, token_hash = create_refresh_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=access_token,
        refresh_token=raw_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user credentials and issue tokens."""
    result = await db.execute(
        select(User).where(User.email == payload.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Prune expired refresh tokens for this user
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.expires_at < datetime.now(UTC),
        )
    )

    raw_token, token_hash = create_refresh_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    await db.commit()

    access_token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=access_token,
        refresh_token=raw_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    """Invalidate the provided refresh token."""
    token_hash = hash_token(payload.refresh_token)
    await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.commit()


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Exchange a valid refresh token for a new access token."""
    token_hash = hash_token(payload.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if refresh_token.expires_at < datetime.now(UTC):
        await db.delete(refresh_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user_result = await db.execute(
        select(User).where(
            User.id == refresh_token.user_id, User.is_active == True
        )
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    access_token = create_access_token(str(user.id))
    return AccessTokenResponse(access_token=access_token)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a password reset token and send an email.
    Always returns 202 to avoid leaking whether an email exists.
    """
    result = await db.execute(
        select(User).where(User.email == payload.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        await db.execute(
            delete(PasswordReset).where(
                PasswordReset.user_id == user.id,
                PasswordReset.used_at == None,  # noqa: E711
            )
        )

        raw_token, token_hash = create_refresh_token()
        reset = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(reset)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email, user.email, user.name, raw_token
        )

    return {"message": "If that email is registered you will receive a reset link shortly"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Verify a reset token and set a new password."""
    token_hash = hash_token(payload.token)

    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used_at == None,  # noqa: E711
        )
    )
    reset = result.scalar_one_or_none()

    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token",
        )

    if reset.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    user_result = await db.execute(
        select(User).where(User.id == reset.user_id, User.is_active == True)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.hashed_password = hash_password(payload.password)
    user.updated_at = datetime.now(UTC)
    reset.used_at = datetime.now(UTC)

    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )

    await db.commit()
    return {"message": "Password updated successfully"}


@router.post("/push-subscription", status_code=status.HTTP_201_CREATED)
async def save_push_subscription(
    payload: PushSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a Web Push subscription for the authenticated user."""
    keys = payload.keys
    p256dh = keys.get("p256dh", "")
    auth_key = keys.get("auth", "")

    if not p256dh or not auth_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="keys must contain p256dh and auth fields",
        )

    subscription = PushSubscription(
        user_id=current_user.id,
        endpoint=payload.endpoint,
        keys_p256dh=p256dh,
        keys_auth=auth_key,
    )
    db.add(subscription)
    await db.commit()
    return {"message": "Push subscription saved"}
