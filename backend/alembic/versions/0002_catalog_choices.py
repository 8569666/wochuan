"""Catalog dictionaries, shared preferences and legacy product links."""

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

from alembic import op

revision = "0002_catalog_choices"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def archive_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
    ]


def upgrade():
    options = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    op.create_table(
        "werp_fabrics",
        *archive_columns(),
        sa.Column("composition", sa.Text(), nullable=False),
        **options,
    )
    op.create_table(
        "werp_categories",
        *archive_columns(),
        sa.Column("last_fabric_id", sa.BigInteger(), sa.ForeignKey("werp_fabrics.id")),
        **options,
    )
    op.create_table(
        "werp_catalog_preferences",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(32), nullable=False, unique=True),
        sa.Column("ids", sa.JSON(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        **options,
    )
    op.add_column("werp_products", sa.Column("category_id", sa.BigInteger(), nullable=True))
    op.add_column("werp_products", sa.Column("fabric_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_product_category", "werp_products", "werp_categories", ["category_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_product_fabric", "werp_products", "werp_fabrics", ["fabric_id"], ["id"]
    )
    # Preserve historical text and create one dictionary row per exact legacy value.
    conn = op.get_bind()
    categories = (
        conn.execute(
            sa.text("SELECT DISTINCT CAST(category AS BINARY) FROM werp_products ORDER BY 1")
        )
        .scalars()
        .all()
    )
    for index, name in enumerate(categories, 1):
        name = name.decode("utf-8")
        conn.execute(
            sa.text(
                "INSERT INTO werp_categories (code,name,status,created_at,updated_at) VALUES (:code,:name,'ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))"
            ),
            {"code": f"LEGACY_C{index}", "name": name},
        )
    fabrics = (
        conn.execute(
            sa.text(
                "SELECT DISTINCT CAST(fabric_composition AS BINARY) FROM werp_products WHERE fabric_composition IS NOT NULL AND fabric_composition<>'' ORDER BY 1"
            )
        )
        .scalars()
        .all()
    )
    for index, composition in enumerate(fabrics, 1):
        composition = composition.decode("utf-8")
        conn.execute(
            sa.text(
                "INSERT INTO werp_fabrics (code,name,composition,status,created_at,updated_at) VALUES (:code,:name,:composition,'ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))"
            ),
            {"code": f"LEGACY_F{index}", "name": composition[:128], "composition": composition},
        )
    op.execute(
        "UPDATE werp_products p JOIN werp_categories c ON BINARY p.category=BINARY c.name SET p.category_id=c.id"
    )
    op.execute(
        "UPDATE werp_products p JOIN werp_fabrics f ON BINARY p.fabric_composition=BINARY f.composition SET p.fabric_id=f.id"
    )
    # Latest successfully saved product supplies the initial category memory.
    for category_id in conn.execute(sa.text("SELECT id FROM werp_categories")).scalars().all():
        fabric_id = conn.execute(
            sa.text(
                "SELECT fabric_id FROM werp_products WHERE category_id=:id ORDER BY updated_at DESC,id DESC LIMIT 1"
            ),
            {"id": category_id},
        ).scalar()
        conn.execute(
            sa.text("UPDATE werp_categories SET last_fabric_id=:fabric WHERE id=:id"),
            {"id": category_id, "fabric": fabric_id},
        )


def downgrade():
    op.drop_constraint("fk_product_fabric", "werp_products", type_="foreignkey")
    op.drop_constraint("fk_product_category", "werp_products", type_="foreignkey")
    op.drop_column("werp_products", "fabric_id")
    op.drop_column("werp_products", "category_id")
    op.drop_table("werp_catalog_preferences")
    op.drop_table("werp_categories")
    op.drop_table("werp_fabrics")
