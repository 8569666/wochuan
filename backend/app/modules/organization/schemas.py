from typing import Literal

from pydantic import Field

from app.common.schemas import ArchiveCreate, partial_schema


class StoreCreate(ArchiveCreate):
    type: Literal["DIRECT", "FRANCHISE", "CONSIGNMENT"] = "DIRECT"
    region: str | None = Field(None, max_length=64)
    address: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=32)


class WarehouseCreate(ArchiveCreate):
    type: Literal["CENTRAL", "STORE", "TRANSIT", "DEFECT"] = "CENTRAL"
    store_id: int | None = Field(None, gt=0)


StoreUpdate = partial_schema(StoreCreate)
WarehouseUpdate = partial_schema(WarehouseCreate)
