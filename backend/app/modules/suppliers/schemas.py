from pydantic import Field

from app.common.schemas import ArchiveCreate, partial_schema


class SupplierCreate(ArchiveCreate):
    contact_name: str | None = Field(None, max_length=64)
    contact_phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=255)
    settlement: str = Field("现结", min_length=1, max_length=32)
    notes: str | None = Field(None, max_length=2000)


SupplierUpdate = partial_schema(SupplierCreate)
