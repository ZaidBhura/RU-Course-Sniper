# Import all models here so that:
# 1. Alembic env.py can import this module to populate Base.metadata for autogenerate
# 2. SQLAlchemy relationship back-references resolve at startup
from app.models.index_state import IndexState
from app.models.notification_channel import NotificationChannel
from app.models.notification_log import NotificationLog
from app.models.tenant import Tenant
from app.models.user import User
from app.models.watched_index import WatchedIndex

__all__ = [
    "Tenant",
    "User",
    "WatchedIndex",
    "NotificationChannel",
    "IndexState",
    "NotificationLog",
]
