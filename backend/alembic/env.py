from sqlalchemy import create_engine

from alembic import context
from app.core.config import get_settings

settings = context.config.attributes.get("settings") or get_settings()
engine = create_engine(
    settings.database_url.set(drivername="mysql+pymysql"),
    connect_args={"init_command": "SET time_zone = '+00:00'"},
)
with engine.connect() as connection:
    context.configure(connection=connection, version_table="werp_alembic_version")
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
