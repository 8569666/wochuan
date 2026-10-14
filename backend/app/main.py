import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.common.responses import error_response, payload
from app.core.config import Settings, get_settings
from app.core.database import make_database
from app.models import register_models


def create_app(settings: Settings | None = None) -> FastAPI:
    register_models()
    settings = settings or get_settings()
    engine, session_factory = make_database(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await engine.dispose()

    app = FastAPI(title="沃川总部管理后台", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    from app.modules.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")
    from app.modules.organization.router import router as org_router
    from app.modules.suppliers.router import router as supplier_router
    app.include_router(org_router, prefix="/api/v1")
    app.include_router(supplier_router, prefix="/api/v1")
    from app.modules.catalog.router import router as catalog_router
    app.include_router(catalog_router, prefix="/api/v1")

    @app.middleware("http")
    async def protect_request(request: Request, call_next):
        request.state.request_id = secrets.token_hex(8)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != settings.app_origin:
                return error_response(403, "请求来源不允许", request.state.request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, str(exc.detail), request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        errors = [{"field": ".".join(str(item) for item in err["loc"]),
                   "message": err["msg"]} for err in exc.errors()]
        return error_response(422, "请检查填写内容", request.state.request_id, errors)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return error_response(503, "数据库暂时不可用，请稍后重试", request.state.request_id)

    @app.get("/api/v1/health/live")
    async def live():
        return payload({"status": "ok"})

    @app.get("/api/v1/health/ready")
    async def ready():
        try:
            async with asyncio.timeout(4):
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            return payload({"status": "ready"})
        except (SQLAlchemyError, TimeoutError, OSError):
            raise HTTPException(503, "数据库暂时不可用，请稍后重试") from None

    return app


app = create_app()
