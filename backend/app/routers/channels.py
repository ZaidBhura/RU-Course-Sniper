import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.security import encrypt_credential
from app.db.session import get_db
from app.models.notification_channel import NotificationChannel
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelOut

router = APIRouter(prefix="/channels", tags=["channels"])


def _build_credential_json(channel_type: str, credential) -> str:
    if channel_type == "discord":
        if not credential.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="discord channel requires webhook_url",
            )
        return json.dumps({"webhook_url": credential.webhook_url})
    # pushover
    if not credential.token or not credential.user_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pushover channel requires token and user_key",
        )
    return json.dumps({"token": credential.token, "user_key": credential.user_key})


@router.get("/", response_model=list[ChannelOut])
async def list_channels(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationChannel)
        .where(
            NotificationChannel.user_id == user.id,
            NotificationChannel.tenant_id == user.tenant_id,
        )
        .order_by(NotificationChannel.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id,
            NotificationChannel.channel_type == body.channel_type,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {body.channel_type} channel already exists",
        )

    blob = encrypt_credential(_build_credential_json(body.channel_type, body.credential))
    channel = NotificationChannel(
        tenant_id=user.tenant_id,
        user_id=user.id,
        channel_type=body.channel_type,
        credential_blob=blob,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.user_id == user.id,
            NotificationChannel.tenant_id == user.tenant_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    channel.is_active = False
    await db.commit()
