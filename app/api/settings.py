"""User settings endpoints (BYOK API key management)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.config import settings
from app.db import get_db
from app.schemas.settings import ApiKeyStatus, ApiKeyUpdate
from app.services import api_key_service

router = APIRouter(tags=["settings"])


@router.get("/settings/api-key-status")
async def get_api_key_status(user: CurrentUser) -> ApiKeyStatus:
    """Return the user's API key status and free run usage."""
    return ApiKeyStatus(
        has_api_key=bool(user.encrypted_api_key),
        free_runs_used=user.free_runs_used,
        free_run_limit=settings.free_run_limit,
        key_last_four=api_key_service.get_key_last_four(user),
    )


@router.put(
    "/settings/api-key",
    responses={422: {"description": "Invalid API key"}},
)
async def update_api_key(
    user: CurrentUser,
    body: ApiKeyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyStatus:
    """Save or update the user's OpenAI API key (validated before storing)."""
    try:
        await api_key_service.save_user_api_key(db, user, body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ApiKeyStatus(
        has_api_key=True,
        free_runs_used=user.free_runs_used,
        free_run_limit=settings.free_run_limit,
        key_last_four=api_key_service.get_key_last_four(user),
    )


@router.delete("/settings/api-key")
async def delete_api_key(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Remove the user's stored API key."""
    await api_key_service.delete_user_api_key(db, user)
    return {"detail": "API key removed"}
