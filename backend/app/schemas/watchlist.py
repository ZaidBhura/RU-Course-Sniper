import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class WatchedIndexCreate(BaseModel):
    index_number: Annotated[int, Field(ge=1, le=99999)]
    label: str | None = Field(default=None, max_length=200)
    semester_code: str = Field(default="12026", pattern=r"^\d{5}$")


class WatchedIndexPatch(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class WatchedIndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    index_number: int
    label: str | None
    course_name: str | None
    semester_code: str
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
