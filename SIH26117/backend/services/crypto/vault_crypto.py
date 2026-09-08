"""Vault-at-rest encryption + key-wrapping (software TEE-hardening layer).

AES-256-GCM file-level encryption. Every uploaded file is stored on disk as an
encrypted blob: ``nonce || ciphertext || tag``. A short-lived per-file Data
Encryption Key (DEK) is itself encrypted ("wrapped") with a long-lived Master
Key that lives outside the vault directory (`AEGIS_VAULT_MASTER_KEY` env or
`/data/keys/vault_master.key`), and the wrapped DEK is stored on the document
row's `wrapped_dek` column. This gives:

  * confidentiality of data at rest (files are ciphertext on disk, and the
    master key is kept off the data volume),
  * per-file key separation (one DEK per document),
  * key-wrapping (a leaked vault blob alone is useless without the master key).

This is a software-hardening approximation of a TEE's confidentiality
boundary — it does NOT claim hardware attestation (SEV-SNP/SGX), it enforces
the same "nothing readable at rest" property on this machine.
"""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_MASTER_KEY_PATH = Path("/data/keys/vault_master.key")
_MASTER_KEY_ENV = "AEGIS_VAULT_MASTER_KEY"
_NONCE_SIZE = 12
_DEK_SIZE = 32

_master_key_cache: bytes | None = None


def _ensure_master_key() -> bytes:
    """Load the master key from env or a file outside the vault; create if absent."""
    global _master_key_cache
    if _master_key_cache is not None:
        return _master_key_cache

    raw = os.environ.get(_MASTER_KEY_ENV)
    if raw:
        # Env var form: either a 32-char passphrase or a 64-char hex key (32 bytes).
        s = raw.strip()
        try:
            if len(s) == 64:
                key = bytes.fromhex(s)
            else:
                key = s.encode("utf-8")
        except Exception as exc:
            raise RuntimeError(
                "AEGIS_VAULT_MASTER_KEY must be 32 bytes (64 hex chars) or a 32-char passphrase"
            ) from exc
        if len(key) != 32:
            raise RuntimeError("AEGIS_VAULT_MASTER_KEY must be exactly 32 bytes")
        _master_key_cache = key
        return key

    if _MASTER_KEY_PATH.exists():
        data = _MASTER_KEY_PATH.read_bytes().strip()
        if len(data) != 32:
            raise RuntimeError(
                f"Master key file {_MASTER_KEY_PATH} must contain exactly 32 bytes"
            )
        _master_key_cache = data
        return data

    _MASTER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    _MASTER_KEY_PATH.write_bytes(key)
    os.chmod(_MASTER_KEY_PATH, 0o600)
    _master_key_cache = key
    logger.warning(
        "vault_master_key_generated",
        path=str(_MASTER_KEY_PATH),
        note="Keep this file safe and out of the data volume; it protects all vault blobs.",
    )
    return key


def vault_encryption_enabled() -> bool:
    """Whether the vault is configured to encrypt new uploads at rest."""
    return bool(getattr(settings, "tee_vault_encryption", True))


def generate_dek() -> tuple[bytes, str]:
    """Create a fresh per-file DEK and return (dek, wrapped_dek_b64)."""
    dek = secrets.token_bytes(_DEK_SIZE)
    wrapped = _wrap_dek(dek)
    return dek, wrapped


def _wrap_dek(dek: bytes) -> str:
    master = _ensure_master_key()
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ct = AESGCM(master).encrypt(nonce, dek, None)
    return base64.b64encode(nonce + ct).decode("ascii")


def unwrap_dek(wrapped_b64: str) -> bytes:
    master = _ensure_master_key()
    blob = base64.b64decode(wrapped_b64)
    nonce, ct = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
    return AESGCM(master).decrypt(nonce, ct, None)


def encrypt_bytes(plaintext: bytes, dek: bytes) -> bytes:
    """Encrypt plaintext -> `nonce || ciphertext || tag` using the file DEK."""
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ct = AESGCM(dek).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_bytes(blob: bytes, dek: bytes) -> bytes:
    """Decrypt a `nonce || ciphertext || tag` blob produced by encrypt_bytes."""
    nonce, ct = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
    return AESGCM(dek).decrypt(nonce, ct, None)


def read_plaintext_file(path: Path, wrapped_dek: str | None) -> bytes:
    """Read + decrypt an encrypted vault file to plaintext bytes."""
    blob = path.read_bytes()
    if not wrapped_dek:
        # Legacy/plaintext file (pre-encryption uploads) — return as-is.
        return blob
    dek = unwrap_dek(wrapped_dek)
    return decrypt_bytes(blob, dek)


def write_encrypted_file(path: Path, plaintext: bytes, dek: bytes) -> None:
    """Encrypt plaintext at-rest and write the blob to disk."""
    blob = encrypt_bytes(plaintext, dek)
    path.write_bytes(blob)


_ATTACHMENT_MAGIC = b"AEGATT1\x00"
_ATTACHMENT_MAGIC_LEN = 8
_ATTACHMENT_LEN_BYTES = 4


def write_attachment_bytes(path: Path, plaintext: bytes, dek: bytes) -> None:
    """Write an image attachment at-rest as an encrypted, self-describing envelope.

    Envelope layout::

        "AEGATT1\\0" || u32(len(wrapped_dek_b64)) || wrapped_dek_b64 || nonce||ct||tag

    Attachments carry no DB row, so the wrapped DEK must travel with the blob
    (documents store theirs on the row instead).
    """
    wrapped = _wrap_dek(dek).encode("utf-8")
    blob = encrypt_bytes(plaintext, dek)
    path.write_bytes(_ATTACHMENT_MAGIC + len(wrapped).to_bytes(4, "big") + wrapped + blob)


def read_attachment_bytes(path: Path) -> bytes:
    """Read an attachment, decrypting envelopes; legacy raw blobs pass through."""
    data = path.read_bytes()
    if not data.startswith(_ATTACHMENT_MAGIC):
        return data
    head = _ATTACHMENT_MAGIC_LEN
    wrapped_len = int.from_bytes(data[head : head + _ATTACHMENT_LEN_BYTES], "big")
    start = head + _ATTACHMENT_LEN_BYTES
    wrapped = data[start : start + wrapped_len].decode("utf-8")
    blob = data[start + wrapped_len :]
    return decrypt_bytes(blob, unwrap_dek(wrapped))


def attestation_fingerprint() -> dict:
    """A stable software-attestation fingerprint (host measurement, not hardware)."""
    master = _ensure_master_key()
    digest = hashlib_sha256(master)
    return {
        "scheme": "aes-256-gcm-keywrap",
        "vault_encrypted": vault_encryption_enabled(),
        "master_key_path": str(_MASTER_KEY_PATH),
        "boot_fingerprint": digest[:16],
        "hardware_attestation": False,
        "note": "Software TEE-hardening (AES-256-GCM at-rest + key-wrapping). No hardware enclave.",
    }


def hashlib_sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()