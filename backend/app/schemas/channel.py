import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_DISCORD_WEBHOOK_PREFIX = "https://discord.com/api/webhooks/"


class ChannelCredential(BaseModel):
    webhook_url: str | None = None
    token: str | None = None
    user_key: str | None = None

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(_DISCORD_WEBHOOK_PREFIX):
            raise ValueError("webhook_url must be a Discord webhook URL")
        return v


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
