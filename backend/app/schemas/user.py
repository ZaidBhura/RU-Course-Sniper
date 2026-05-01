import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_superuser: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPatch(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None
