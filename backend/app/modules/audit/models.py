from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Base, Record


class AuditLog(Record, Base):
    __tablename__ = "werp_audit_logs"
    __table_args__ = TABLE_OPTIONS
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    action: Mapped[str] = mapped_column(String(32))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(BigInteger)
    changes: Mapped[dict] = mapped_column(JSON)
