import httpx
import pymysql
import pytest

from app.core.config import get_settings
from app.core.database import make_database
from app.core.migrations import upgrade_database
from app.models import Base


def assert_test_database(settings, development):
    if settings.database != "codex_werp_test" or settings.database == development.database:
        raise RuntimeError("测试只允许使用独立 codex_werp_test 库")


@pytest.fixture(scope="session")
def test_settings():
    development = get_settings()
    settings = development.model_copy(
        update={"database": "codex_werp_test", "app_origin": "http://test"}
    )
    assert_test_database(settings, development)
    conn = pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.username,
        password=settings.password.get_secret_value(),
        charset="utf8mb4",
    )
    with conn.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS codex_werp_test CHARACTER SET utf8mb4")
    conn.close()
    upgrade_database(settings)
    return settings


@pytest.fixture
async def db_session(test_settings):
    engine, factory = make_database(test_settings)
    async with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
async def client(test_settings, db_session):
    from app.main import create_app

    app = create_app(test_settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://test"},
    ) as value:
        yield value
    await app.state.engine.dispose()


@pytest.fixture
async def authenticated_client(client, db_session):
    from app.modules.auth.models import User
    from app.modules.auth.security import hash_password

    db_session.add(User(username="tester", password_hash=hash_password("Test!Password#123")))
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login", json={"username": "tester", "password": "Test!Password#123"}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
async def matrix(authenticated_client):
    client = authenticated_client
    category = await client.post("/api/v1/categories", json={"code": "DRESS", "name": "连衣裙"})
    assert category.status_code == 201
    colors = []
    for i, name in enumerate(["米白", "樱花粉", "曜石黑"], 1):
        response = await client.post("/api/v1/colors", json={"code": f"C{i}", "name": name})
        assert response.status_code == 201
        colors.append(response.json()["data"])
    group = await client.post(
        "/api/v1/size-groups",
        json={
            "code": "WOMEN",
            "name": "女装标准尺码",
            "sizes": [{"code": code, "name": code} for code in ["S", "M", "L", "XL"]],
        },
    )
    assert group.status_code == 201
    group = group.json()["data"]
    return {
        "code": "2026S-DR088",
        "name": "法式收腰连衣裙",
        "category": "连衣裙",
        "category_id": category.json()["data"]["id"],
        "year": 2026,
        "season": "春夏",
        "tag_price": "599.00",
        "purchase_base_price": "140.00",
        "color_ids": [c["id"] for c in colors],
        "size_group_id": group["id"],
        "skus": [
            {"color_id": c["id"], "size_id": s["id"], "retail_price": "599.00"}
            for c in colors
            for s in group["sizes"]
        ],
    }
