import httpx

from app.core.config import Settings
from app.main import create_app


async def test_live_does_not_require_database():
    app = create_app(Settings(_env_file=None))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200


async def test_ready_returns_503_when_db_unavailable():
    app = create_app(Settings(_env_file=None, MYSQL_PORT=1))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert "password" not in response.text
