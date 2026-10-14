from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Archive, Base


class Supplier(Archive, Base):
    __tablename__ = "werp_suppliers"
    __table_args__ = TABLE_OPTIONS
    contact_name: Mapped[str | None] = mapped_column(String(64))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(255))
    settlement: Mapped[str] = mapped_column(String(32), default="现结")
    notes: Mapped[str | None] = mapped_column(Text)
