"""Schemas for user settings (BYOK API key management)."""

from pydantic import BaseModel, Field


class ApiKeyUpdate(BaseModel):
    api_key: str = Field(..., min_length=10)


class ApiKeyStatus(BaseModel):
    has_api_key: bool
    free_runs_used: int
    free_run_limit: int
    key_last_four: str | None = None
