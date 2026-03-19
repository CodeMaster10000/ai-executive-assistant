from datetime import datetime

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    """Request body for creating a new user profile workspace."""

    name: str = Field(..., min_length=1, max_length=200)
    targets: list[str] | None = None
    constraints: list[str] | None = None
    skills: list[str] | None = None


class ProfileUpdate(BaseModel):
    """Request body for partially updating an existing user profile."""

    name: str | None = Field(None, min_length=1, max_length=200)
    targets: list[str] | None = None
    constraints: list[str] | None = None
    skills: list[str] | None = None


class ProfileRead(BaseModel):
    """Read-only representation of a user profile returned by the API."""

    id: str
    name: str
    targets: list[str] | None = None
    constraints: list[str] | None = None
    skills: list[str] | None = None
    cv_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileExport(BaseModel):
    """Portable profile data for export and import between systems."""

    name: str
    targets: list[str] | None = None
    constraints: list[str] | None = None
    skills: list[str] | None = None
