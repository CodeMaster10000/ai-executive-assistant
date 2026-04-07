"""Schema for job opportunity API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOpportunityRead(BaseModel):
    """Read-only representation of a job opportunity returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    run_id: str
    title: str
    company: str | None = None
    url: str | None = None
    description: str | None = None
    location: str | None = None
    salary_range: str | None = None
    source_query: str | None = None
    created_at: datetime
