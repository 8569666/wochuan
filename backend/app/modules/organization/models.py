from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Archive, Base


class Store(Archive, Base):
    __tablename__ = "werp_stores"
    __table_args__ = TABLE_OPTIONS
    type: Mapped[str] = mapped_column(String(16), default="DIRECT")
    region: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))


class Warehouse(Archive, Base):
    __tablename__ = "werp_warehouses"
    __table_args__ = TABLE_OPTIONS
    type: Mapped[str] = mapped_column(String(16), default="CENTRAL")
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_stores.id"), unique=True
    )
