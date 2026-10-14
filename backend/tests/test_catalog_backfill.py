from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.models import Base


def test_legacy_backfill_preserves_exact_text_and_last_fabric(test_settings):
    assert test_settings.database == "codex_werp_test"
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    config.attributes["settings"] = test_settings
    engine = create_engine(test_settings.database_url.set(drivername="mysql+pymysql"))
    try:
        with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
        command.downgrade(config, "0001_foundation")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO werp_size_groups (code,name,status,created_at,updated_at) VALUES ('LEGACY','旧尺码','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))"
                )
            )
            group_id = connection.scalar(
                text("SELECT id FROM werp_size_groups WHERE code='LEGACY'")
            )
            for index, (category, fabric) in enumerate([("Dress", "Cotton"), ("dress", "cotton")]):
                connection.execute(
                    text(
                        "INSERT INTO werp_products (code,name,category,fabric_composition,year,season,tag_price,size_group_id,safety_category,status,created_at,updated_at) VALUES (:code,'旧商品',:category,:fabric,2026,'春夏',99,:group_id,'B类','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))"
                    ),
                    {
                        "code": f"LEGACY{index}",
                        "category": category,
                        "fabric": fabric,
                        "group_id": group_id,
                    },
                )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT p.category,p.fabric_composition,c.name,f.composition,c.last_fabric_id,p.fabric_id FROM werp_products p LEFT JOIN werp_categories c ON c.id=p.category_id LEFT JOIN werp_fabrics f ON f.id=p.fabric_id ORDER BY p.code"
                )
            ).all()
            assert len(rows) == 2
            assert all(
                row.category == row.name
                and row.fabric_composition == row.composition
                and row.last_fabric_id == row.fabric_id
                for row in rows
            )
    finally:
        command.upgrade(config, "head")
        engine.dispose()
