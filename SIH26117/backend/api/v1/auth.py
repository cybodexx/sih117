"""Auth routes — login, refresh, logout, me, register."""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user
from backend.core.exceptions import Conflict, NotFound, Unauthorized
from backend.core.rbac import Clearance, Role, ServerUserContext
from backend.db.models.user import UserModel
from backend.db.session import get_db
from backend.schemas.auth import (
    AuthLogin,
    AuthTokenResponse,
    RefreshRequest,
    RegisterUser,
    UserRead,
)
from backend.services.security import (
    async_create_access_token,
    check_lockout,
    clear_failures,
    create_refresh_token,
    dummy_verify,
    hash_password,
    record_failure,
    verify_password,
)
from backend.services.audit.writer import emit as audit_emit

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _user_to_read(user: UserModel) -> UserRead:
    return UserRead(
        id=str(user.id),
        username=user.username,
        full_name=user.full_name or "",
        role=user.role,
        clearance_level=user.clearance_level,
        departments=user.departments or [],
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: AuthLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(UserModel).where(UserModel.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        await dummy_verify()
        await audit_emit(
            "LOGIN_FAILED",
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
            resource_type="auth",
            severity="warning",
        )
        raise Unauthorized("Invalid credentials")

    if check_lockout(str(user.id)):
        raise Unauthorized("Account locked. Try again later.")

    if not await verify_password(body.password, user.password_hash):
        record_failure(str(user.id))
        await audit_emit(
            "LOGIN_FAILED",
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
            user_id=str(user.id),
            role=user.role,
            resource_type="auth",
            severity="warning",
        )
        raise Unauthorized("Invalid credentials")

    clear_failures(str(user.id))

    access = await async_create_access_token(
        str(user.id), user.role, user.clearance_level, user.departments or []
    )
    refresh = create_refresh_token()

    await audit_emit(
        "LOGIN_SUCCESS",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=str(user.id),
        role=user.role,
        resource_type="auth",
        severity="info",
    )

    logger.info("user_login", user_id=str(user.id), username=user.username)
    return AuthTokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_min * 60,
        user=_user_to_read(user),
    )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Validate refresh token and re-issue access + refresh pair."""
    result = await db.execute(
        select(UserModel).where(UserModel.is_active.is_(True))
    )
    users = result.scalars().all()

    # Stub: accept any non-empty refresh token for now.
    # Production would store hashed refresh tokens in a table.
    if not body.refresh_token:
        raise Unauthorized("Invalid refresh token")

    # For a dev stub, pick the first active user to re-issue against
    # In production, decode session from refresh token.
    if not users:
        raise Unauthorized("No active users found")

    target = users[0]
    access = await async_create_access_token(
        str(target.id), target.role, target.clearance_level, target.departments or []
    )
    new_refresh = create_refresh_token()

    logger.info("token_refresh", user_id=str(target.id))
    return AuthTokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_ttl_min * 60,
        user=_user_to_read(target),
    )


@router.post("/logout", status_code=204)
async def logout(
    user: Annotated[ServerUserContext, Depends(get_current_user)],
):
    """Client-side token discard. No server-side state in this stub."""
    logger.info("user_logout", user_id=user.user_id)
    return Response(status_code=204)


@router.get("/me", response_model=UserRead)
async def get_me(
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(UserModel).where(UserModel.id == user.user_id)
    )
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise NotFound("User not found")
    return _user_to_read(db_user)


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    body: RegisterUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Dev-only registration endpoint. Creates a new user in the DB."""
    existing = await db.execute(
        select(UserModel).where(UserModel.username == body.username)
    )
    if existing.scalar_one_or_none() is not None:
        raise Conflict(f"Username '{body.username}' already exists")

    hashed = await hash_password(body.password)
    role = Role(body.role.upper()) if body.role.upper() in {r.value for r in Role} else Role.VIEWER
    clearance = max(Clearance.PUBLIC, min(Clearance.RESTRICTED, body.clearance_level))
    new_user = UserModel(
        username=body.username,
        full_name=body.full_name,
        password_hash=hashed,
        role=role.value,
        clearance_level=clearance.value,
        departments=body.departments,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    await audit_emit(
        "USER_REGISTERED",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=str(new_user.id),
        role=new_user.role,
        resource_type="user",
        resource_id=str(new_user.id),
        severity="info",
    )

    logger.info("user_registered", user_id=str(new_user.id), username=new_user.username)
    return _user_to_read(new_user)
