"""Bcrypt-based password hashing and verification."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with 12 rounds of salting.

    Args:
        password: The plaintext password to hash.

    Returns:
        A bcrypt-hashed password string.
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash.

    Args:
        plain: The plaintext password to verify.
        hashed: The bcrypt-hashed password to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
