import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    index_number: int
    semester_code: str
    channel_type: str
    event_type: str
    delivery_status: str
    error_message: str | None
    course_subject: str | None
    course_number: str | None
    course_title: str | None
    webreg_url: str | None
    created_at: datetime
