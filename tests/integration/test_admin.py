"""Tests for admin endpoints."""

import pytest


@pytest.mark.asyncio
async def test_admin_list_users(client, admin_headers):
    """Verify that an admin user can list all registered users.

    Args:
        client: The httpx test client.
        admin_headers: Auth headers for the admin user.
    """
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_admin_forbidden_for_regular_user(client, auth_headers):
    """Verify that a non-admin user receives 403 Forbidden on admin endpoints.

    Args:
        client: The httpx test client.
        auth_headers: Auth headers for a regular user.
    """
    resp = await client.get("/api/admin/users", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_unauthenticated(client):
    """Verify that unauthenticated requests to admin endpoints return 401.

    Args:
        client: The httpx test client.
    """
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401
