import sys

import httpx
import pymysql
import pytest
from sqlalchemy import text

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
    settings = development.model_copy(update={"database": "codex_werp_test",
                                              "app_origin": "http://test"})
    assert_test_database(settings, development)
    conn = pymysql.connect(host=settings.host, port=settings.port,
                           user=settings.username, password=settings.password.get_secret_value(),
                           charset="utf8mb4")
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
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                base_url="http://test", headers={"Origin": "http://test"}) as value:
        yield value
    await app.state.engine.dispose()
