from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReceivingQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_id: int = Field(gt=0)
    size_id: int = Field(gt=0)
    quantity: int = Field(strict=True, ge=1, le=1000000)


class ReceivingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    supplier_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    unit_cost: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    quantities: list[ReceivingQuantity] = Field(min_length=1, max_length=900)

    @field_validator("quantities")
    @classmethod
    def unique_cells(cls, values):
        if len({(cell.color_id, cell.size_id) for cell in values}) != len(values):
            raise ValueError("进货规格不能重复")
        return values
