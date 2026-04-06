"""Tests for Fernet-based API key encryption."""

import pytest
from unittest.mock import patch

from app.auth.encryption import decrypt_api_key, encrypt_api_key


def test_encrypt_decrypt_round_trip():
    plain = "sk-test-key-1234567890abcdef"
    encrypted = encrypt_api_key(plain)
    assert encrypted != plain
    assert decrypt_api_key(encrypted) == plain


def test_different_keys_produce_different_ciphertext():
    key1 = encrypt_api_key("sk-key-aaaaaa")
    key2 = encrypt_api_key("sk-key-bbbbbb")
    assert key1 != key2


def test_corrupted_ciphertext_raises():
    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_api_key("this-is-not-valid-fernet-token")


def test_different_secret_cannot_decrypt():
    encrypted = encrypt_api_key("sk-secret-key-12345")

    class FakeSettings:
        api_key_encryption_secret = "totally-different-secret"

    with patch("app.auth.encryption.settings", FakeSettings()):
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_api_key(encrypted)
