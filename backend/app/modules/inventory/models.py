from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Base, Record


class PurchaseReceipt(Record, Base):
    __tablename__ = "werp_purchase_receipts"
    __table_args__ = TABLE_OPTIONS
    number: Mapped[str] = mapped_column(String(40), unique=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    supplier_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_suppliers.id"))
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_warehouses.id"))
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("werp_products.id"))
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_quantity: Mapped[int] = mapped_column(BigInteger, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"))


class PurchaseReceiptLine(Record, Base):
    __tablename__ = "werp_purchase_receipt_lines"
    __table_args__ = (UniqueConstraint("receipt_id", "sku_id"), TABLE_OPTIONS)
    receipt_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_purchase_receipts.id"))
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_skus.id"))
    quantity: Mapped[int] = mapped_column(BigInteger)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))


class StockBalance(Record, Base):
    __tablename__ = "werp_stock_balances"
    __table_args__ = (UniqueConstraint("warehouse_id", "sku_id"), TABLE_OPTIONS)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_warehouses.id"))
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_skus.id"))
    quantity: Mapped[int] = mapped_column(BigInteger, default=0)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=Decimal("0"))


class StockMovement(Record, Base):
    __tablename__ = "werp_stock_movements"
    __table_args__ = TABLE_OPTIONS
    receipt_line_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("werp_purchase_receipt_lines.id"), unique=True
    )
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_warehouses.id"))
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_skus.id"))
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    before_quantity: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(BigInteger)
    after_quantity: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
