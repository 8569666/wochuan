from sqlalchemy import JSON, BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Archive, Base, Record


class Role(Archive, Base):
    __tablename__ = "werp_roles"
    __table_args__ = TABLE_OPTIONS
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class UserRoleGrant(Record, Base):
    __tablename__ = "werp_user_role_grants"
    __table_args__ = (UniqueConstraint("user_id", "role_id", "scope_type"), TABLE_OPTIONS)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_roles.id"))
    scope_type: Mapped[str] = mapped_column(String(16))
    scope_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
