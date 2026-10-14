import copy
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator


class ArchiveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return value
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError("编码只允许英文字母、数字、下划线和短横线")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("名称不能为空")
        return value


def partial_schema(schema):
    fields = {}
    for name, field in schema.model_fields.items():
        cloned = copy.deepcopy(field)
        cloned.default = None
        fields[name] = (field.annotation | None, cloned)
    return create_model(f"{schema.__name__}Update", __base__=schema, **fields)
