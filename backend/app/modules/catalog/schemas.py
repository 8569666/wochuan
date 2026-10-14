import re
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.schemas import ArchiveCreate, partial_schema

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ColorCreate(ArchiveCreate):
    code: str = Field(min_length=1, max_length=16)
    hex_value: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("code")
    @classmethod
    def dictionary_code(cls, value):
        if value is not None and not re.fullmatch(r"[A-Z0-9_]+", value):
            raise ValueError("颜色和尺码编码只允许字母、数字和下划线")
        return value


class SizeCreate(ColorCreate):
    hex_value: None = None


class SizeGroupCreate(ArchiveCreate):
    sizes: list[SizeCreate] = Field(min_length=1, max_length=30)

    @field_validator("sizes")
    @classmethod
    def unique_sizes(cls, value):
        if value is not None and len({s.code for s in value}) != len(value):
            raise ValueError("尺码编码不能重复")
        return value


class SKUCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_id: int = Field(gt=0)
    size_id: int = Field(gt=0)
    retail_price: Money
    barcode: str | None = Field(None, max_length=64)

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value):
        if value is not None:
            value = value.strip()
            if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
                raise ValueError("条码需为非空英文字母、数字或_-组合")
        return value


class ProductFields(ArchiveCreate):
    category: str = Field(min_length=1, max_length=64)
    year: int = Field(ge=1900, le=2100)
    season: str = Field(min_length=1, max_length=16)
    wave_band: str | None = Field(None, max_length=32)
    fabric_composition: str | None = Field(None, max_length=2000)
    safety_category: str = Field("B类", min_length=1, max_length=32)
    tag_price: Money
    purchase_base_price: Money | None = None
    min_retail_price: Money | None = None


class ProductCreate(ProductFields):
    color_ids: list[int] = Field(min_length=1, max_length=30)
    size_group_id: int = Field(gt=0)
    skus: list[SKUCreate] = Field(min_length=1, max_length=900)


class SKUPrice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(gt=0)
    retail_price: Money


class ProductUpdate(partial_schema(ProductFields)):
    sku_prices: list[SKUPrice] | None = None


ColorUpdate = partial_schema(ColorCreate)
SizeGroupUpdate = partial_schema(SizeGroupCreate)
