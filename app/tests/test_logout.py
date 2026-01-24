from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_invalidates_token(client: AsyncClient):
    # 1. Register and login to get a token
    email = f"test_{uuid4()}@example.com"
    password = "Password123!"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Logout Test"},
    )

    login_res = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify token works
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    # 3. Logout
    logout_res = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # 4. Verify token no longer works
    me_res_after = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res_after.status_code == 401
    assert me_res_after.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_logout_without_token_fails(client: AsyncClient):
    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_request_missing_jti_is_rejected(client: AsyncClient):
    # This might happen if using an old token without JTI
    # 1. Manually create a token without JTI if we can, or just trust the middleware logic
    # In our case, the middleware now REQUIRES jti.
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.config import get_settings

    settings = get_settings()
    payload = {
        "sub": str(uuid4()),
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "could not validate credentials" in res.json()["detail"].lower()
