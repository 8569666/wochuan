import pytest
from sqlalchemy import inspect

from app.core.config import Settings
from app.core.migrations import upgrade_database
from app.models import Base
from conftest import assert_test_database


def test_refuse_development_database_cleanup():
    settings = Settings(_env_file=None, database="codex_db")
    with pytest.raises(RuntimeError):
        assert_test_database(settings, settings)


async def test_migration_roundtrip_on_test_database(test_settings, db_session):
    connection = await db_session.connection()
    tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
    assert all(name in tables for name in Base.metadata.tables)
    assert "werp_alembic_version" in tables
    assert all(name.startswith("werp_") for name in tables)
