from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Base, Record


class User(Record, Base):
    __tablename__ = "werp_users"
    __table_args__ = TABLE_OPTIONS
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128), default="总部管理员")
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="ADMIN")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")


class LoginSession(Record, Base):
    __tablename__ = "werp_sessions"
    __table_args__ = TABLE_OPTIONS
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), index=True)


class AuthLimit(Base):
    __tablename__ = "werp_auth_limits"
    __table_args__ = TABLE_OPTIONS
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
