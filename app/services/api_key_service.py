"""Service for managing user-provided LLM API keys (BYOK)."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_api_key, encrypt_api_key
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def validate_openai_key(api_key: str) -> bool:
    """Check whether an OpenAI API key is valid by hitting the models endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


async def save_user_api_key(db: AsyncSession, user: User, plain_key: str) -> None:
    """Validate, encrypt, and store the API key on the user record."""
    if not await validate_openai_key(plain_key):
        raise ValueError("The provided API key is invalid or could not be verified")
    user.encrypted_api_key = encrypt_api_key(plain_key)
    await db.commit()


def get_user_api_key(user: User) -> str | None:
    """Decrypt and return the user's stored API key, or None if not set."""
    if not user.encrypted_api_key:
        return None
    return decrypt_api_key(user.encrypted_api_key)


async def delete_user_api_key(db: AsyncSession, user: User) -> None:
    """Remove the stored API key."""
    user.encrypted_api_key = None
    await db.commit()


def get_key_last_four(user: User) -> str | None:
    """Return the last 4 characters of the stored key for display, or None."""
    if not user.encrypted_api_key:
        return None
    plain = decrypt_api_key(user.encrypted_api_key)
    return f"...{plain[-4:]}"


def resolve_api_key(user: User) -> str:
    """Determine which API key to use for a run.

    - Admin users always get the app's global key.
    - Users with their own key stored always use it.
    - Users within the free run limit get the app's global key.
    - Otherwise raises ValueError (must provide own key).
    """
    if user.role == "admin":
        if not settings.api_key:
            raise ValueError("Server API key is not configured")
        return settings.api_key

    own_key = get_user_api_key(user)
    if own_key:
        return own_key

    if user.free_runs_used < settings.free_run_limit:
        if not settings.api_key:
            raise ValueError("Server API key is not configured")
        return settings.api_key

    raise ValueError(
        "Free trial exhausted. Please add your own OpenAI API key in Settings to continue."
    )
