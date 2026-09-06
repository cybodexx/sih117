"""JWT and password hashing. M3 — the single auth module."""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

from backend.core.config import get_settings
from backend.core.exceptions import Unauthorized
from backend.core.rbac import Clearance, Role, ServerUserContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# In-memory failed-attempt tracker (production: use Redis)
_failed_attempts: dict[str, tuple[int, float]] = {}
_LOCKOUT_THRESHOLD = 5
_LOCKOUT_SECONDS = 900


def _load_key(path: Path) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path.write_bytes(pem)
        pub = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        settings = get_settings()
        settings.jwt_public_key_path.write_bytes(pub)
        return pem.decode()
    return path.read_text()


def _get_keys() -> tuple[str, str]:
    settings = get_settings()
    return _load_key(settings.jwt_private_key_path), _load_key(settings.jwt_public_key_path)


_private_key: str | None = None
_public_key: str | None = None


def _ensure_keys() -> tuple[str, str]:
    global _private_key, _public_key
    if _private_key is None:
        _private_key, _public_key = _get_keys()
    return _private_key, _public_key


def create_access_token(user_id: str, role: str, clearance: int, departments: list[str]) -> str:
    priv, _ = _ensure_keys()
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "clearance_level": clearance,
        "departments": departments,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_min),
    }
    return jwt.encode(payload, priv, algorithm="RS256", headers={"kid": "aegis-k1"})


async def async_create_access_token(
    user_id: str, role: str, clearance: int, departments: list[str]
) -> str:
    return await run_in_threadpool(create_access_token, user_id, role, clearance, departments)


def decode_access_token(token: str) -> ServerUserContext:
    _, pub = _ensure_keys()
    try:
        payload = jwt.decode(token, pub, algorithms=["RS256"])
        return ServerUserContext(
            user_id=payload["sub"],
            role=Role(payload["role"]),
            clearance_level=Clearance(payload["clearance_level"]),
            departments=payload["departments"],
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Invalid or expired token") from exc


async def hash_password(password: str) -> str:
    return await run_in_threadpool(pwd_context.hash, password)


async def verify_password(plain: str, hashed: str) -> bool:
    return await run_in_threadpool(pwd_context.verify, plain, hashed)


async def dummy_verify() -> None:
    """Constant-time dummy verify to prevent user enumeration."""
    await run_in_threadpool(pwd_context.verify, "dummy", "$2b$12$nVglmuB3tHEp9zncCADq/e5UD.hCcHcEU/Jhv5.AJEdp.jxbFf8D.")


def check_lockout(user_id: str) -> bool:
    attempts, locked_at = _failed_attempts.get(user_id, (0, 0.0))
    if attempts >= _LOCKOUT_THRESHOLD:
        if time.time() - locked_at < _LOCKOUT_SECONDS:
            return True
        _failed_attempts.pop(user_id, None)
    return False


def record_failure(user_id: str) -> None:
    attempts, _ = _failed_attempts.get(user_id, (0, 0.0))
    _failed_attempts[user_id] = (attempts + 1, time.time())


def clear_failures(user_id: str) -> None:
    _failed_attempts.pop(user_id, None)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
