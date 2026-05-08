from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_api_db
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.schemas.log import NotificationLogOut

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=list[NotificationLogOut])
async def list_logs(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    result = await db.execute(
        select(NotificationLog)
        .where(
            NotificationLog.user_id == user.id,
            NotificationLog.tenant_id == user.tenant_id,
        )
        .order_by(NotificationLog.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
