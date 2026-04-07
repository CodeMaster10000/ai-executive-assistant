"""Schema for read-only policy file API responses."""

from pydantic import BaseModel


class PolicyRead(BaseModel):
    """Read-only representation of a policy file returned by the API."""

    name: str
    content: dict
