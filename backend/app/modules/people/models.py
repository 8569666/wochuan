from datetime import date

from sqlalchemy import JSON, BigInteger, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TABLE_OPTIONS, Archive, Base, Record


class OrgUnit(Archive, Base):
    __tablename__ = "werp_org_units"
    __table_args__ = TABLE_OPTIONS
    kind: Mapped[str] = mapped_column(String(24))
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_org_units.id", ondelete="SET NULL")
    )
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_stores.id"), unique=True
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_warehouses.id"), unique=True
    )


class Position(Archive, Base):
    __tablename__ = "werp_positions"
    __table_args__ = TABLE_OPTIONS


class Employee(Archive, Base):
    __tablename__ = "werp_employees"
    __table_args__ = TABLE_OPTIONS
    status: Mapped[str] = mapped_column(String(16), default="PROBATION")
    phone: Mapped[str | None] = mapped_column(String(32))
    personnel_type: Mapped[str] = mapped_column(String(24), default="EMPLOYEE")
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_org_units.id"))
    org_unit_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_org_units.id"))
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_positions.id"))
    manager_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_employees.id", ondelete="SET NULL")
    )
    hire_date: Mapped[date] = mapped_column(Date)
    confirmation_date: Mapped[date | None] = mapped_column(Date)
    left_date: Mapped[date | None] = mapped_column(Date)


class Assignment(Record, Base):
    __tablename__ = "werp_assignments"
    __table_args__ = TABLE_OPTIONS
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_employees.id"))
    org_unit_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_org_units.id"))
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_positions.id"))
    manager_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("werp_employees.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class PersonnelEvent(Record, Base):
    __tablename__ = "werp_personnel_events"
    __table_args__ = TABLE_OPTIONS
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_employees.id"))
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("werp_users.id"))
    kind: Mapped[str] = mapped_column(String(24))
    effective_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(255))
    handover_employee_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("werp_employees.id")
    )
    handover_notes: Mapped[str | None] = mapped_column(Text)
    before_data: Mapped[dict] = mapped_column(JSON)
    after_data: Mapped[dict] = mapped_column(JSON)
