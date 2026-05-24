from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.components.com_contact.models import ContactMessage
from src.components.com_contact.service import (
    count_messages,
    count_unread,
    create_message,
    delete_message,
    get_or_create_settings,
    list_messages,
    mark_read,
    save_settings,
)


# ---------------------------------------------------------------------------
# service layer
# ---------------------------------------------------------------------------


async def test_get_or_create_settings_defaults(db_session: AsyncSession):
    s = await get_or_create_settings(db_session)
    assert s.id == 1
    assert s.enabled is True
    assert s.recipient_email == ""
    assert s.subject_prefix == "[Kontakt]"
    assert s.notify_sender is False


async def test_save_settings(db_session: AsyncSession):
    await save_settings(
        db_session,
        enabled=False,
        recipient_email="admin@example.com",
        subject_prefix="[Web]",
        notify_sender=True,
    )
    s = await get_or_create_settings(db_session)
    assert s.enabled is False
    assert s.recipient_email == "admin@example.com"
    assert s.subject_prefix == "[Web]"
    assert s.notify_sender is True


async def test_create_message(db_session: AsyncSession):
    msg = await create_message(
        db_session,
        name="Jan Novák",
        email="jan@example.com",
        subject="Dotaz",
        message="Dobrý den, mám dotaz.",
    )
    assert msg.id is not None
    assert msg.name == "Jan Novák"
    assert msg.is_read is False


async def test_list_and_count_messages(db_session: AsyncSession):
    for i in range(3):
        await create_message(
            db_session,
            name=f"User {i}",
            email=f"user{i}@test.com",
            subject="",
            message="Zpráva",
        )
    total = await count_messages(db_session)
    msgs = await list_messages(db_session)
    assert total == 3
    assert len(msgs) == 3


async def test_count_unread(db_session: AsyncSession):
    msg = await create_message(
        db_session, name="A", email="a@a.com", subject="", message="msg"
    )
    assert await count_unread(db_session) == 1
    await mark_read(db_session, msg.id)
    assert await count_unread(db_session) == 0


async def test_mark_read(db_session: AsyncSession):
    msg = await create_message(
        db_session, name="A", email="a@a.com", subject="", message="msg"
    )
    updated = await mark_read(db_session, msg.id)
    assert updated is not None
    assert updated.is_read is True


async def test_mark_read_missing(db_session: AsyncSession):
    result = await mark_read(db_session, 99999)
    assert result is None


async def test_delete_message(db_session: AsyncSession):
    msg = await create_message(
        db_session, name="A", email="a@a.com", subject="", message="msg"
    )
    removed = await delete_message(db_session, msg.id)
    assert removed is True
    assert await count_messages(db_session) == 0


async def test_delete_message_missing(db_session: AsyncSession):
    assert await delete_message(db_session, 99999) is False


async def test_list_pagination(db_session: AsyncSession):
    for i in range(5):
        await create_message(
            db_session, name=f"U{i}", email=f"u{i}@t.com", subject="", message="x"
        )
    first = await list_messages(db_session, limit=2, offset=0)
    second = await list_messages(db_session, limit=2, offset=2)
    assert len(first) == 2
    assert len(second) == 2
    assert first[0].id != second[0].id


# ---------------------------------------------------------------------------
# web frontend
# ---------------------------------------------------------------------------


async def test_contact_form_get(client: AsyncClient):
    resp = await client.get("/kontakt", follow_redirects=False)
    assert resp.status_code == 200
    assert b"form" in resp.content.lower()


async def test_contact_form_post_valid(client: AsyncClient, db_session: AsyncSession):
    resp = await client.post(
        "/kontakt",
        data={
            "name": "Jan",
            "email": "jan@example.com",
            "subject": "Test",
            "message": "Testovací zpráva.",
            "website": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/kontakt"
    assert await count_messages(db_session) == 1


async def test_contact_form_post_honeypot(client: AsyncClient, db_session: AsyncSession):
    resp = await client.post(
        "/kontakt",
        data={
            "name": "Bot",
            "email": "bot@spam.com",
            "subject": "Buy now",
            "message": "Click here",
            "website": "http://spam.com",  # honeypot filled
        },
        follow_redirects=False,
    )
    # Should redirect silently (as if success)
    assert resp.status_code == 303
    # But no message saved
    assert await count_messages(db_session) == 0


async def test_contact_form_post_missing_fields(client: AsyncClient):
    resp = await client.post(
        "/kontakt",
        data={"name": "", "email": "", "message": "", "website": ""},
        follow_redirects=False,
    )
    # Re-renders form with errors (200, not redirect)
    assert resp.status_code == 200


async def test_contact_form_disabled(client: AsyncClient, db_session: AsyncSession):
    await save_settings(
        db_session,
        enabled=False,
        recipient_email="",
        subject_prefix="[K]",
        notify_sender=False,
    )
    resp = await client.get("/kontakt", follow_redirects=False)
    assert resp.status_code == 200
    # Form should not appear (or disabled message shown)


# ---------------------------------------------------------------------------
# admin routes
# ---------------------------------------------------------------------------


async def test_admin_inbox_requires_auth(client: AsyncClient):
    resp = await client.get("/admin/com_contact", follow_redirects=False)
    assert resp.status_code in (302, 303)


async def test_admin_inbox_authenticated(auth_client: AsyncClient):
    resp = await auth_client.get("/admin/com_contact", follow_redirects=False)
    assert resp.status_code == 200


async def test_admin_inbox_shows_messages(auth_client: AsyncClient, db_session: AsyncSession):
    await create_message(
        db_session, name="Testovací", email="t@t.com", subject="Předmět", message="Zpráva"
    )
    resp = await auth_client.get("/admin/com_contact", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Testov" in resp.content


async def test_admin_mark_read(auth_client: AsyncClient, db_session: AsyncSession):
    msg = await create_message(
        db_session, name="A", email="a@a.com", subject="", message="msg"
    )
    resp = await auth_client.post(
        f"/admin/com_contact/{msg.id}/read", follow_redirects=False
    )
    assert resp.status_code == 303
    updated = await mark_read(db_session, msg.id)
    assert updated is not None


async def test_admin_delete(auth_client: AsyncClient, db_session: AsyncSession):
    msg = await create_message(
        db_session, name="A", email="a@a.com", subject="", message="msg"
    )
    resp = await auth_client.post(
        f"/admin/com_contact/{msg.id}/delete", follow_redirects=False
    )
    assert resp.status_code == 303
    assert await count_messages(db_session) == 0


async def test_admin_settings_get(auth_client: AsyncClient):
    resp = await auth_client.get("/admin/com_contact/settings", follow_redirects=False)
    assert resp.status_code == 200


async def test_admin_settings_save(auth_client: AsyncClient, db_session: AsyncSession):
    resp = await auth_client.post(
        "/admin/com_contact/settings",
        data={
            "enabled": "on",
            "recipient_email": "test@example.com",
            "subject_prefix": "[Test]",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    s = await get_or_create_settings(db_session)
    assert s.recipient_email == "test@example.com"
    assert s.subject_prefix == "[Test]"
