from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CourseRead(BaseModel):
    """Read-only representation of a course opportunity returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    run_id: str
    title: str
    platform: str | None = None
    url: str | None = None
    description: str | None = None
    cost: str | None = None
    duration: str | None = None
    created_at: datetime
