from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Archive, Base, Record


class Color(Archive, Base):
    __tablename__ = "werp_colors"
    __table_args__ = TABLE_OPTIONS
    hex_value: Mapped[str | None] = mapped_column(String(7))


class SizeGroup(Archive, Base):
    __tablename__ = "werp_size_groups"
    __table_args__ = TABLE_OPTIONS


class Size(Archive, Base):
    __tablename__ = "werp_sizes"
    __table_args__ = (UniqueConstraint("group_id", "code"), TABLE_OPTIONS)
    code: Mapped[str] = mapped_column(String(16))
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_size_groups.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Product(Archive, Base):
    __tablename__ = "werp_products"
    __table_args__ = TABLE_OPTIONS
    category: Mapped[str] = mapped_column(String(64))
    year: Mapped[int] = mapped_column(Integer)
    season: Mapped[str] = mapped_column(String(16))
    wave_band: Mapped[str | None] = mapped_column(String(32))
    fabric_composition: Mapped[str | None] = mapped_column(Text)
    safety_category: Mapped[str] = mapped_column(String(32), default="B类")
    tag_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    purchase_base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_retail_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    size_group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_size_groups.id"))


class SKU(Record, Base):
    __tablename__ = "werp_skus"
    __table_args__ = (UniqueConstraint("product_id", "color_id", "size_id"), TABLE_OPTIONS)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_products.id"))
    color_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_colors.id"))
    size_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_sizes.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    barcode: Mapped[str] = mapped_column(String(64), unique=True)
    retail_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
