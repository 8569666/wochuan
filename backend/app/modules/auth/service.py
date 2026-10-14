import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import utcnow
from app.modules.audit.service import record_audit
from app.modules.auth.models import AuthLimit, LoginSession, User
from app.modules.auth.security import hash_password, token_hash, verify_password

SessionDep = Annotated[AsyncSession, Depends(get_session)]
DUMMY_PASSWORD = hash_password(secrets.token_urlsafe(32))


def user_data(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


async def require_admin(request: Request, session: SessionDep) -> User:
    token = request.cookies.get("werp_session", "")
    user = (
        await session.scalar(
            select(User)
            .join(LoginSession)
            .where(
                LoginSession.token_hash == token_hash(token),
                LoginSession.expires_at > utcnow(),
                User.status == "ACTIVE",
            )
        )
        if token
        else None
    )
    if user is None:
        raise HTTPException(401, "请先登录")
    if user.role != "ADMIN":
        raise HTTPException(403, "没有操作权限")
    return user


AdminDep = Annotated[User, Depends(require_admin)]


async def authenticate(session: AsyncSession, username: str, password: str, ip: str):
    username = username.strip().lower()
    now = utcnow()
    key = token_hash(f"{username}|{ip}")
    stmt = insert(AuthLimit).values(key=key, failures=0, window_start=now)
    await session.execute(stmt.on_duplicate_key_update(key=key))
    limit = await session.scalar(select(AuthLimit).where(AuthLimit.key == key).with_for_update())
    if limit.window_start < now - timedelta(minutes=15):
        limit.failures = 0
        limit.window_start = now
    if limit.failures >= 5:
        await session.rollback()
        raise HTTPException(429, "登录尝试过多，请15分钟后再试")
    user = await session.scalar(select(User).where(User.username == username))
    correct = verify_password(password, user.password_hash if user else DUMMY_PASSWORD)
    if not correct or not user or user.status != "ACTIVE" or user.role != "ADMIN":
        limit.failures += 1
        await session.commit()
        raise HTTPException(401, "用户名或密码不正确")
    limit.failures = 0
    token = secrets.token_urlsafe(32)
    session.add(
        LoginSession(
            user_id=user.id, token_hash=token_hash(token), expires_at=now + timedelta(hours=8)
        )
    )
    record_audit(session, user.id, "LOGIN", "user", user.id, {})
    await session.commit()
    return user, token
