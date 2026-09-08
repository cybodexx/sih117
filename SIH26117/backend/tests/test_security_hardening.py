"""Security-hardening integration tests (run against the live stack).

Covers the defects found in review:
  1. Refresh-token impersonation is impossible (unknown/replayed tokens -> 401).
  2. /auth/register requires auth and non-admins cannot mint privileged roles.
  3. Document read routes enforce can_read (get/file/list), and unready docs
     are never served.

Requires the running api container (Postgres + Redis).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import httpx
import pytest

from backend.core.rbac import Clearance, Role
from backend.services.security import async_create_access_token

API = "http://api:8000"
LOGIN = {"username": "green3511", "password": "Aegis@2026"}


# --- DB + auth helpers ----------------------------------------------------------


async def _insert_doc(doc_id: str, dept: str, clearance: int, status: str) -> None:
    from backend.core.config import get_settings
    from backend.db.base import async_session
    from backend.db.models.document import DocumentModel
    from backend.services.crypto.vault_crypto import generate_dek, write_encrypted_file

    dek, wrapped = generate_dek()
    vault = Path(get_settings().vault_path)
    vault.mkdir(parents=True, exist_ok=True)
    storage = vault / f"test-{doc_id}.bin"
    write_encrypted_file(storage, b"TOP-SECRET-PAYLOAD", dek)

    async with async_session() as db:
        d = DocumentModel(
            id=uuid.UUID(doc_id),
            owner_id=uuid.uuid4(),
            filename="shielded.txt",
            mime="text/plain",
            size_bytes=10,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=str(storage),
            wrapped_dek=wrapped,
            clearance_level=clearance,
            department=dept,
            status=status,
        )
        db.add(d)
        await db.commit()


async def _remove_doc(doc_id: str) -> None:
    from backend.db.base import async_session
    from backend.db.models.document import DocumentModel

    async with async_session() as db:
        d = await db.get(DocumentModel, uuid.UUID(doc_id))
        if d:
            storage = Path(d.storage_key)
            if storage.exists():
                storage.unlink(missing_ok=True)
            await db.delete(d)
            await db.commit()


async def _set_status(doc_id: str, status: str) -> None:
    from backend.db.base import async_session
    from backend.db.models.document import DocumentModel
    from sqlalchemy import select

    async with async_session() as db:
        d = (
            await db.execute(
                select(DocumentModel).where(DocumentModel.id == uuid.UUID(doc_id))
            )
        ).scalar_one()
        d.status = status
        await db.commit()


async def _remove_user(username: str) -> None:
    from backend.db.base import async_session
    from backend.db.models.user import UserModel
    from sqlalchemy import select

    async with async_session() as db:
        u = (
            await db.execute(select(UserModel).where(UserModel.username == username))
        ).scalar_one_or_none()
        if u:
            await db.delete(u)
            await db.commit()


async def _jwt(role: Role, departments: list[str], clearance: Clearance) -> str:
    return await async_create_access_token(
        str(uuid.uuid4()), role.value, clearance.value, departments
    )


async def _login(client: httpx.AsyncClient) -> dict:
    r = await client.post(f"{API}/api/v1/auth/login", json=LOGIN)
    assert r.status_code == 200, r.text
    return r.json()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "security: live-stack security integration test (needs api/redis/postgres)",
    )


@pytest.fixture(autouse=True)
async def _fresh_engine_loop():
    """pytest-asyncio gives each test a new event loop; dispose pooled
    connections around each test so the engine never reuses cross-loop
    handles (also drops handles left behind by other test files)."""
    from backend.db.base import engine

    await engine.dispose()
    yield
    await engine.dispose()


# --- Defect 1: refresh-token impersonation -------------------------------------


@pytest.mark.anyio
async def test_refresh_garbage_token_rejected():
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{API}/api/v1/auth/refresh",
            json={"refresh_token": "not-a-real-token-abc"},
        )
        assert r.status_code == 401


@pytest.mark.anyio
async def test_refresh_empty_token_rejected():
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": ""})
        assert r.status_code == 401


@pytest.mark.anyio
async def test_refresh_real_token_binds_to_same_user():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        r = await client.post(
            f"{API}/api/v1/auth/refresh",
            json={"refresh_token": data["refresh_token"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["user"]["username"] == LOGIN["username"]
        assert r.json()["refresh_token"] != data["refresh_token"]


@pytest.mark.anyio
async def test_refresh_token_is_single_use():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        rt = data["refresh_token"]
        first = await client.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": rt})
        assert first.status_code == 200
        second = await client.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": rt})
        assert second.status_code == 401


@pytest.mark.anyio
async def test_refresh_rejects_arbitrary_syntactic_tokens():
    async with httpx.AsyncClient(timeout=20) as client:
        for tok in ["x" * 32, "A" * 48, "-" * 32, uuid.uuid4().hex]:
            r = await client.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": tok})
            assert r.status_code == 401, (tok[:8], r.status_code)


# --- Defect 2: register ------------------------------------------------------------


@pytest.mark.anyio
async def test_register_requires_auth():
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{API}/api/v1/auth/register",
            json={"username": "nobody", "password": "supersecret1", "role": "VIEWER"},
        )
        assert r.status_code == 401


@pytest.mark.anyio
async def test_register_nonadmin_cannot_mint_admin():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        head = {"Authorization": f"Bearer {data['access_token']}"}
        r = await client.post(
            f"{API}/api/v1/auth/register",
            headers=head,
            json={
                "username": "evil-admin",
                "password": "supersecret1",
                "role": "ADMIN",
                "clearance_level": 3,
            },
        )
        assert r.status_code == 403


@pytest.mark.anyio
async def test_register_nonadmin_cannot_mint_engineer():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        head = {"Authorization": f"Bearer {data['access_token']}"}
        r = await client.post(
            f"{API}/api/v1/auth/register",
            headers=head,
            json={
                "username": "evil-engineer",
                "password": "supersecret1",
                "role": "ENGINEER",
                "clearance_level": 2,
            },
        )
        assert r.status_code == 403


@pytest.mark.anyio
async def test_register_clearance_bounded_by_actor():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        head = {"Authorization": f"Bearer {data['access_token']}"}
        uname = f"bounded-{uuid.uuid4().hex[:6]}"
        r = await client.post(
            f"{API}/api/v1/auth/register",
            headers=head,
            json={
                "username": uname,
                "password": "supersecret1",
                "role": "VIEWER",
                "clearance_level": 3,
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["clearance_level"] <= 2
        await _remove_user(uname)


@pytest.mark.anyio
async def test_register_viewer_ok_then_username_taken():
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _login(client)
        head = {"Authorization": f"Bearer {data['access_token']}"}
        uname = f"viewer-{uuid.uuid4().hex[:6]}"
        r = await client.post(
            f"{API}/api/v1/auth/register",
            headers=head,
            json={
                "username": uname,
                "password": "supersecret1",
                "role": "VIEWER",
                "clearance_level": 1,
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "VIEWER"
        dup = await client.post(
            f"{API}/api/v1/auth/register",
            headers=head,
            json={"username": uname, "password": "supersecret1", "role": "VIEWER"},
        )
        assert dup.status_code == 409
        await _remove_user(uname)


# --- Defect 3: document RBAC ----------------------------------------------------------


@pytest.mark.anyio
async def test_rbac_doc_visibility_matrix():
    """A single MECH/PUBLIC/READY doc is visible only to MECH-dept, >=PUBLIC actors."""
    doc_id = str(uuid.uuid4())
    await _insert_doc(doc_id, "MECH", Clearance.PUBLIC.value, "READY")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            cases = [
                ("ENGINEER", ["MECH"], 2, True),
                ("ENGINEER", ["ADMIN"], 2, False),  # wrong department
                ("VIEWER", ["MECH"], 0, True),
                ("ANALYST", ["MECH"], 1, True),
                ("ADMIN", ["HR"], 3, True),  # cross-department
                ("AUDITOR", ["HR"], 3, True),  # cross-department
            ]
            for role, depts, clev, expect_ok in cases:
                token = await _jwt(Role(role), depts, Clearance(clev))
                head = {"Authorization": f"Bearer {token}"}
                r = await client.get(f"{API}/api/v1/documents/{doc_id}", headers=head)
                assert (r.status_code == 200) == expect_ok, (role, depts, r.status_code)
                if expect_ok:
                    f = await client.get(f"{API}/api/v1/documents/{doc_id}/file", headers=head)
                    assert f.status_code == 200, (role, f.status_code)
        finally:
            await _remove_doc(doc_id)


@pytest.mark.anyio
async def test_rbac_doc_denied_above_clearance():
    """A RESTRICTED doc is not served to a CONFIDENTIAL clearance actor."""
    doc_id = str(uuid.uuid4())
    await _insert_doc(doc_id, "MECH", Clearance.RESTRICTED.value, "READY")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            token = await _jwt(Role.ENGINEER, ["MECH"], Clearance(2))
            head = {"Authorization": f"Bearer {token}"}
            r = await client.get(f"{API}/api/v1/documents/{doc_id}", headers=head)
            assert r.status_code == 404
        finally:
            await _remove_doc(doc_id)


@pytest.mark.anyio
async def test_rbac_list_hides_docs_above_clearance():
    doc_id = str(uuid.uuid4())
    await _insert_doc(doc_id, "MECH", Clearance.RESTRICTED.value, "READY")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            low = await _jwt(Role.VIEWER, ["MECH"], Clearance(0))
            page = await client.get(
                f"{API}/api/v1/documents?status=READY&size=100",
                headers={"Authorization": f"Bearer {low}"},
            )
            items = page.json()["items"]
            assert not any(d["id"] == doc_id for d in items)
        finally:
            await _remove_doc(doc_id)


@pytest.mark.anyio
async def test_rbac_unready_doc_never_readable():
    doc_id = str(uuid.uuid4())
    await _insert_doc(doc_id, "MECH", Clearance.PUBLIC.value, "READY")
    await _set_status(doc_id, "PROCESSING")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            token = await _jwt(Role.ENGINEER, ["MECH"], Clearance(2))
            head = {"Authorization": f"Bearer {token}"}
            r = await client.get(f"{API}/api/v1/documents/{doc_id}", headers=head)
            assert r.status_code == 404
        finally:
            await _remove_doc(doc_id)