from fastapi import APIRouter, Request, Response
from sqlalchemy import delete

from app.common.responses import payload
from app.modules.audit.service import record_audit
from app.modules.auth.models import LoginSession
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.security import token_hash
from app.modules.auth.service import AdminDep, SessionDep, authenticate, user_data

router = APIRouter(prefix="/auth", tags=["登录"])


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response, session: SessionDep):
    user, token = await authenticate(session, body.username, body.password,
                                      request.client.host if request.client else "local")
    response.set_cookie("werp_session", token, httponly=True, samesite="strict", max_age=28800,
                        secure=request.app.state.settings.cookie_secure, path="/")
    return payload(user_data(user))


@router.get("/me")
async def me(user: AdminDep):
    return payload(user_data(user))


@router.post("/logout")
async def logout(request: Request, response: Response, session: SessionDep, user: AdminDep):
    await session.execute(delete(LoginSession).where(
        LoginSession.token_hash == token_hash(request.cookies.get("werp_session", ""))))
    record_audit(session, user.id, "LOGOUT", "user", user.id, {})
    await session.commit()
    response.delete_cookie("werp_session", path="/", httponly=True, samesite="strict")
    return payload()
