"""Auth routes — login, refresh, logout, me, register."""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user
from backend.core.exceptions import Conflict, Forbidden, NotFound, Unauthorized
from backend.core.rbac import Clearance, MAX_CLEARANCE, Role, ServerUserContext
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
    resolve_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
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
    await store_refresh_token(
        refresh, str(user.id), settings.refresh_token_ttl_h * 3600
    )

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
    """Validate a stored refresh token (SHA-256) and re-issue access + a new
    refresh pair. Rejects unknown/expired/replayed tokens so no user can
    impersonate another."""
    if not body.refresh_token:
        raise Unauthorized("Invalid refresh token")

    bound_user_id = await resolve_refresh_token(body.refresh_token)
    if bound_user_id is None:
        await audit_emit(
            "REFRESH_REJECTED",
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
            resource_type="auth",
            severity="warning",
        )
        raise Unauthorized("Invalid refresh token")

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == bound_user_id, UserModel.is_active.is_(True)
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise Unauthorized("Invalid refresh token")

    # Rotate: the presented token is single-use, a fresh pair is issued.
    await rotate_refresh_token(body.refresh_token, settings.refresh_token_ttl_h * 3600)

    access = await async_create_access_token(
        str(target.id), target.role, target.clearance_level, target.departments or []
    )
    new_refresh = create_refresh_token()
    await store_refresh_token(
        new_refresh, str(target.id), settings.refresh_token_ttl_h * 3600
    )

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
    body: RefreshRequest | None = None,
):
    """Server-side revocation: invalidate the presented refresh token."""
    if body is not None and body.refresh_token:
        await rotate_refresh_token(body.refresh_token, settings.refresh_token_ttl_h * 3600)
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


# Roles that grant broad access; only an ADMIN (or better) may mint them.
# A non-admin acts only up to the max the administrators have granted that actor.
_PRIVILEGED_ROLES = frozenset({Role.ENGINEER, Role.AUDITOR, Role.ADMIN})


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    actor: Annotated[ServerUserContext, Depends(get_current_user)],
    body: RegisterUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new user. Requires an authenticated actor; role and clearance
    self-escalation is blocked (only ADMIN can grant ENGINEER/AUDITOR/ADMIN,
    and the granted clearance cannot exceed the creating actor's)."""
    requested_role = Role(body.role.upper()) if body.role.upper() in {r.value for r in Role} else Role.VIEWER

    # Non-admin actors may never mint privileged roles.
    if requested_role in _PRIVILEGED_ROLES and actor.role is not Role.ADMIN:
        raise Forbidden(
            f"Only an ADMIN can create a {requested_role.value} account"
        )

    existing = await db.execute(
        select(UserModel).where(UserModel.username == body.username)
    )
    if existing.scalar_one_or_none() is not None:
        raise Conflict(f"Username '{body.username}' already exists")

    # Clamp the granted clearance: no more than the actor themselves has, and
    # allow the requested value only within that bound.
    max_grantable = Clearance(
        min(Clearance.RESTRICTED.value, actor.clearance_level.value)
    )
    clearance = Clearance(
        max(
            Clearance.PUBLIC.value,
            min(body.clearance_level, max_grantable.value),
        )
    )
    # A non-admin creating a role is capped to that role's MAX_CLEARANCE too.
    if actor.role is not Role.ADMIN:
        clearance = Clearance(
            min(clearance.value, MAX_CLEARANCE[requested_role].value)
        )

    hashed = await hash_password(body.password)
    new_user = UserModel(
        username=body.username,
        full_name=body.full_name,
        password_hash=hashed,
        role=requested_role.value,
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

    logger.info(
        "user_registered",
        user_id=str(new_user.id),
        username=new_user.username,
        actor_id=actor.user_id,
    )
    return _user_to_read(new_user)
