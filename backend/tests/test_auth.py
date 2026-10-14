import hashlib
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import utcnow
from app.modules.auth.models import LoginSession, User
from app.modules.auth.security import hash_password, verify_password


def test_password_special_characters_roundtrip():
    password = " space#'@:/?密码 "
    encoded = hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password(password.strip(), encoded)
    assert password not in encoded


@pytest.fixture
async def admin(db_session):
    user = User(username="tester", password_hash=hash_password("Test!Password#123"))
    db_session.add(user)
    await db_session.commit()
    return user


async def login(client):
    return await client.post("/api/v1/auth/login", json={"username": "tester", "password": "Test!Password#123"})


async def test_login_logout_and_expiry(client, admin, db_session):
    response = await login(client)
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    token = client.cookies.get("werp_session")
    record = await db_session.scalar(select(LoginSession).where(
        LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    record.expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await login(client)).status_code == 200
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_disabled_user_and_missing_cookie_rejected(client, admin, db_session):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    await login(client)
    admin.status = "INACTIVE"
    await db_session.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_wrong_origin_rejected(client):
    response = await client.post("/api/v1/auth/login", headers={"origin": "https://evil.example"}, json={})
    assert response.status_code == 403


async def test_failed_login_rate_limit(client, admin):
    for _ in range(5):
        response = await client.post("/api/v1/auth/login", json={"username": "tester", "password": "bad"})
        assert response.status_code == 401
    assert (await login(client)).status_code == 429
