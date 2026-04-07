"""Fernet-based encryption for user API keys stored at rest."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet() -> Fernet:
    raw = settings.api_key_encryption_secret.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt a plaintext API key for safe storage.

    Args:
        plain_key: The raw API key string to encrypt.

    Returns:
        A Fernet-encrypted, base64-encoded string.
    """
    return _get_fernet().encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a previously encrypted API key back to plaintext.

    Args:
        encrypted_key: The Fernet-encrypted key string.

    Returns:
        The original plaintext API key.

    Raises:
        ValueError: If decryption fails, typically because the encryption secret changed.
    """
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt API key -- encryption secret may have changed") from exc
