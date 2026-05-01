import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChannelCredential(BaseModel):
    # discord:  {"webhook_url": "..."}
    # pushover: {"token": "...", "user_key": "..."}
    webhook_url: str | None = None
    token: str | None = None
    user_key: str | None = None


class ChannelCreate(BaseModel):
    channel_type: str = Field(pattern=r"^(discord|pushover)$")
    credential: ChannelCredential


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
