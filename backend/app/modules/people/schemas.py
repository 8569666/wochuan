from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.common.schemas import ArchiveCreate, partial_schema

Kind = Literal["COMPANY", "HQ", "REGION", "DEPARTMENT", "STORE", "WAREHOUSE"]
PersonnelType = Literal["EMPLOYEE", "CONTRACTOR", "PARTNER", "TEMP"]
EmploymentStatus = Literal["PENDING", "PROBATION", "ACTIVE", "LEFT"]


class OrgCreate(ArchiveCreate):
    kind: Kind
    parent_id: int | None = Field(None, gt=0)
    store_id: int | None = Field(None, gt=0)
    warehouse_id: int | None = Field(None, gt=0)


OrgUpdate = partial_schema(OrgCreate)


class EmployeeCreate(ArchiveCreate):
    phone: str | None = Field(None, max_length=32)
    personnel_type: PersonnelType = "EMPLOYEE"
    status: Literal["PENDING", "PROBATION", "ACTIVE"] = "PROBATION"
    company_id: int | None = Field(None, gt=0)
    org_unit_id: int = Field(gt=0)
    position_id: int = Field(gt=0)
    manager_id: int | None = Field(None, gt=0)
    hire_date: date


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=128)
    phone: str | None = Field(None, max_length=32)
    personnel_type: PersonnelType | None = None

    @field_validator("name", "phone", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class GrantItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: int = Field(gt=0)
    scope_type: Literal["ALL", "ORG_TREE", "STORES", "WAREHOUSES", "HOME", "SELF"]
    scope_ids: list[int] = Field(default_factory=list, max_length=100)


class GrantsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grants: list[GrantItem] = Field(max_length=30)


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["ONBOARD", "CONFIRM", "TRANSFER", "LEAVE"]
    effective_date: date
    reason: str | None = Field(None, max_length=255)
    org_unit_id: int | None = Field(None, gt=0)
    position_id: int | None = Field(None, gt=0)
    manager_id: int | None = Field(None, gt=0)
    handover_employee_id: int | None = Field(None, gt=0)
    handover_notes: str | None = Field(None, max_length=2000)
    grants: list[GrantItem] | None = Field(None, max_length=30)


class RoleCreate(ArchiveCreate):
    permissions: list[str] = Field(default_factory=list, max_length=100)


RoleUpdate = partial_schema(RoleCreate)


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    password: SecretStr = Field(min_length=12, max_length=256)
    enabled: bool = True


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    password: SecretStr | None = Field(None, min_length=12, max_length=256)
