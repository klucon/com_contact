from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ContactMessage, ContactSettings


async def get_or_create_settings(db: AsyncSession) -> ContactSettings:
    s = (
        await db.execute(select(ContactSettings).where(ContactSettings.id == 1))
    ).scalar_one_or_none()
    if s is None:
        s = ContactSettings(id=1)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


async def save_settings(
    db: AsyncSession,
    *,
    enabled: bool,
    recipient_email: str,
    subject_prefix: str,
    notify_sender: bool,
) -> ContactSettings:
    s = await get_or_create_settings(db)
    s.enabled = enabled
    s.recipient_email = recipient_email.strip()
    s.subject_prefix = subject_prefix.strip()
    s.notify_sender = notify_sender
    s.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(s)
    return s


async def create_message(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
    ip_address: str = "",
) -> ContactMessage:
    msg = ContactMessage(
        name=name.strip(),
        email=email.strip(),
        subject=subject.strip(),
        message=message.strip(),
        ip_address=ip_address,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_messages(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[ContactMessage]:
    q = (
        select(ContactMessage)
        .order_by(ContactMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await db.execute(q)).scalars().all())


async def count_messages(db: AsyncSession) -> int:
    return (
        await db.execute(select(func.count()).select_from(ContactMessage))
    ).scalar_one()


async def count_unread(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(ContactMessage)
            .where(ContactMessage.is_read.is_(False))
        )
    ).scalar_one()


async def mark_read(db: AsyncSession, message_id: int) -> ContactMessage | None:
    msg = (
        await db.execute(
            select(ContactMessage).where(ContactMessage.id == message_id)
        )
    ).scalar_one_or_none()
    if msg is None:
        return None
    msg.is_read = True
    await db.commit()
    await db.refresh(msg)
    return msg


async def delete_message(db: AsyncSession, message_id: int) -> bool:
    msg = (
        await db.execute(
            select(ContactMessage).where(ContactMessage.id == message_id)
        )
    ).scalar_one_or_none()
    if msg is None:
        return False
    await db.delete(msg)
    await db.commit()
    return True
