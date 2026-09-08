"""Unit tests for the vault-at-rest crypto layer (AES-256-GCM + key-wrapping)."""
from __future__ import annotations

import secrets

from backend.services.crypto import vault_crypto


def test_encrypt_decrypt_roundtrip():
    dek = secrets.token_bytes(32)
    plaintext = b"TOP SECRET refinery incident report data \x00\xff binary"
    blob = vault_crypto.encrypt_bytes(plaintext, dek)
    assert blob != plaintext
    assert plaintext[4:20] not in blob  # not a plaintext prefix leak
    out = vault_crypto.decrypt_bytes(blob, dek)
    assert out == plaintext


def test_decrypt_wrong_key_fails():
    dek = secrets.token_bytes(32)
    other = secrets.token_bytes(32)
    blob = vault_crypto.encrypt_bytes(b"secret", dek)
    try:
        vault_crypto.decrypt_bytes(blob, other)
        assert False, "should have raised"
    except Exception:
        pass


def test_encrypt_nonce_is_random():
    dek = secrets.token_bytes(32)
    a = vault_crypto.encrypt_bytes(b"same", dek)
    b = vault_crypto.encrypt_bytes(b"same", dek)
    assert a != b


def test_key_wrap_unwrap_roundtrip(monkeypatch):
    monkeypatch.setenv("AEGIS_VAULT_MASTER_KEY", secrets.token_bytes(32).hex())
    vault_crypto._master_key_cache = None
    dek = secrets.token_bytes(32)
    wrapped = vault_crypto._wrap_dek(dek)
    unwrapped = vault_crypto.unwrap_dek(wrapped)
    assert unwrapped == dek
    vault_crypto._master_key_cache = None


def test_generate_dek_produces_opaque_wrapped_key(monkeypatch):
    monkeypatch.setenv("AEGIS_VAULT_MASTER_KEY", secrets.token_bytes(32).hex())
    vault_crypto._master_key_cache = None
    dek, wrapped = vault_crypto.generate_dek()
    assert len(dek) == 32
    assert len(wrapped) > 0 and wrapped.isascii()
    assert vault_crypto.unwrap_dek(wrapped) == dek
    vault_crypto._master_key_cache = None


def test_attestation_fingerprint_shape(monkeypatch):
    monkeypatch.setenv("AEGIS_VAULT_MASTER_KEY", secrets.token_bytes(32).hex())
    vault_crypto._master_key_cache = None
    fp = vault_crypto.attestation_fingerprint()
    assert fp["scheme"] == "aes-256-gcm-keywrap"
    assert fp["hardware_attestation"] is False
    assert len(fp["boot_fingerprint"]) == 16
    vault_crypto._master_key_cache = None


def test_attachment_envelope_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_VAULT_MASTER_KEY", secrets.token_bytes(32).hex())
    vault_crypto._master_key_cache = None
    dek = secrets.token_bytes(32)
    plaintext = b"\x89PNG\r\n\x1a\n" + secrets.token_bytes(512)
    path = tmp_path / "att.img"
    vault_crypto.write_attachment_bytes(path, plaintext, dek)
    blob = path.read_bytes()
    assert blob.startswith(vault_crypto._ATTACHMENT_MAGIC)
    assert blob != plaintext
    assert plaintext[:8] not in blob
    out = vault_crypto.read_attachment_bytes(path)
    assert out == plaintext
    vault_crypto._master_key_cache = None


def test_attachment_legacy_raw_passthrough(tmp_path):
    raw = b"\x89PNG\r\n\x1a\nlegacy plaintext bytes"
    path = tmp_path / "old.img"
    path.write_bytes(raw)
    assert vault_crypto.read_attachment_bytes(path) == raw


def test_attachment_tamper_detected(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_VAULT_MASTER_KEY", secrets.token_bytes(32).hex())
    vault_crypto._master_key_cache = None
    dek = secrets.token_bytes(32)
    path = tmp_path / "att.img"
    vault_crypto.write_attachment_bytes(path, b"secret image", dek)
    blob = bytearray(path.read_bytes())
    blob[-1] ^= 0xFF
    path.write_bytes(bytes(blob))
    try:
        vault_crypto.read_attachment_bytes(path)
        assert False, "tampered envelope should raise"
    except Exception:
        pass
    vault_crypto._master_key_cache = None