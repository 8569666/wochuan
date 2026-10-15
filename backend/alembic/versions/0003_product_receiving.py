"""Atomic purchase receipts, stock balances and movements."""

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

from alembic import op

revision = "0003_product_receiving"
down_revision = "0002_catalog_choices"
branch_labels = None
depends_on = None


def base_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
    ]


def foreign(name, target, nullable=False, unique=False):
    return sa.Column(name, sa.BigInteger(), sa.ForeignKey(target), nullable=nullable, unique=unique)


def upgrade():
    options = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    op.create_table(
        "werp_purchase_receipts",
        *base_columns(),
        sa.Column("number", sa.String(40), nullable=False, unique=True),
        sa.Column("request_id", sa.String(36), nullable=False, unique=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        foreign("supplier_id", "werp_suppliers.id"),
        foreign("warehouse_id", "werp_warehouses.id"),
        foreign("product_id", "werp_products.id", nullable=True),
        foreign("actor_id", "werp_users.id"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_quantity", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.Numeric(20, 2), nullable=False),
        **options,
    )
    op.create_table(
        "werp_purchase_receipt_lines",
        *base_columns(),
        foreign("receipt_id", "werp_purchase_receipts.id"),
        foreign("sku_id", "werp_skus.id"),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.UniqueConstraint("receipt_id", "sku_id"),
        **options,
    )
    op.create_table(
        "werp_stock_balances",
        *base_columns(),
        foreign("warehouse_id", "werp_warehouses.id"),
        foreign("sku_id", "werp_skus.id"),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("average_cost", sa.Numeric(20, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(24, 4), nullable=False),
        sa.UniqueConstraint("warehouse_id", "sku_id"),
        **options,
    )
    op.create_table(
        "werp_stock_movements",
        *base_columns(),
        foreign("receipt_line_id", "werp_purchase_receipt_lines.id", unique=True),
        foreign("warehouse_id", "werp_warehouses.id"),
        foreign("sku_id", "werp_skus.id"),
        foreign("actor_id", "werp_users.id"),
        sa.Column("before_quantity", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("after_quantity", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        **options,
    )


def downgrade():
    for table in [
        "werp_stock_movements",
        "werp_stock_balances",
        "werp_purchase_receipt_lines",
        "werp_purchase_receipts",
    ]:
        op.drop_table(table)
