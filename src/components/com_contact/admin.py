from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.admin.deps import CurrentAdminUser
from src.api.admin.render import admin_render
from src.core.acl import require_admin_permission
from src.database.base import get_db_session

from .service import (
    count_messages,
    count_unread,
    create_message,
    delete_message,
    get_or_create_settings,
    list_messages,
    mark_read,
    save_settings,
)

router = APIRouter(prefix="/admin/com_contact", tags=["com_contact"])

_PAGE_SIZE = 50


@router.get("", response_class=HTMLResponse)
async def inbox(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.view")),
    db: AsyncSession = Depends(get_db_session),
    page: int = 1,
) -> HTMLResponse:
    page = max(1, page)
    offset = (page - 1) * _PAGE_SIZE
    messages = await list_messages(db, limit=_PAGE_SIZE, offset=offset)
    total = await count_messages(db)
    unread = await count_unread(db)
    pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    flash = request.session.pop("flash", None)
    return await admin_render(
        "admin/com_contact/inbox.html",
        request,
        db,
        user=current_user,
        messages=messages,
        total=total,
        unread=unread,
        page=page,
        pages=pages,
        flash=flash,
    )


@router.get("/new", response_class=HTMLResponse)
async def new_get(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.manage")),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    return await admin_render(
        "admin/com_contact/new.html",
        request,
        db,
        user=current_user,
        errors={},
        form={},
        flash=None,
    )


@router.post("/new")
async def new_post(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.manage")),
    db: AsyncSession = Depends(get_db_session),
    name: str = Form(""),
    email: str = Form(""),
    subject: str = Form(""),
    message: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    errors: dict[str, str] = {}
    if not name.strip():
        errors["name"] = "Jméno je povinné."
    if not email.strip() or "@" not in email:
        errors["email"] = "Zadejte platný e-mail."
    if not message.strip():
        errors["message"] = "Zpráva je povinná."
    if errors:
        return await admin_render(
            "admin/com_contact/new.html",
            request,
            db,
            user=current_user,
            errors=errors,
            form={"name": name, "email": email, "subject": subject, "message": message},
            flash=None,
        )
    await create_message(db, name=name, email=email, subject=subject, message=message)
    request.session["flash"] = {"type": "success", "text": "Zpráva byla přidána."}
    return RedirectResponse("/admin/com_contact", status_code=303)


@router.post("/{message_id}/read")
async def read(
    request: Request,
    message_id: int,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.view")),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    await mark_read(db, message_id)
    return RedirectResponse("/admin/com_contact", status_code=303)


@router.post("/{message_id}/delete")
async def delete(
    request: Request,
    message_id: int,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.manage")),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    await delete_message(db, message_id)
    request.session["flash"] = {"type": "success", "text": "Zpráva smazána."}
    return RedirectResponse("/admin/com_contact", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def settings_get(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.manage")),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    settings = await get_or_create_settings(db)
    flash = request.session.pop("flash", None)
    return await admin_render(
        "admin/com_contact/settings.html",
        request,
        db,
        user=current_user,
        settings=settings,
        flash=flash,
    )


@router.post("/settings")
async def settings_post(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("contact.manage")),
    db: AsyncSession = Depends(get_db_session),
    enabled: str | None = Form(None),
    recipient_email: str = Form(""),
    subject_prefix: str = Form("[Kontakt]"),
    notify_sender: str | None = Form(None),
) -> RedirectResponse:
    await save_settings(
        db,
        enabled=enabled is not None,
        recipient_email=recipient_email,
        subject_prefix=subject_prefix,
        notify_sender=notify_sender is not None,
    )
    request.session["flash"] = {"type": "success", "text": "Nastavení uloženo."}
    return RedirectResponse("/admin/com_contact/settings", status_code=303)
