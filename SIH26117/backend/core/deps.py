from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.concurrency import run_in_threadpool

from backend.core.config import get_settings
from backend.core.exceptions import Unauthorized
from backend.core.rbac import Clearance, Role, ServerUserContext
from backend.services.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> ServerUserContext:
    """Extract and verify the user identity from the JWT."""
    try:
        ctx = await run_in_threadpool(decode_access_token, token)
        return ctx
    except Unauthorized:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*roles: Role):
    """Dependency that gates on role membership."""

    async def _check(user: Annotated[ServerUserContext, Depends(get_current_user)]):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
            )
        return user

    return _check


def require_clearance(level: Clearance):
    """Dependency that gates on minimum clearance level."""

    async def _check(user: Annotated[ServerUserContext, Depends(get_current_user)]):
        if user.clearance_level < level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient clearance",
            )
        return user

    return _check
