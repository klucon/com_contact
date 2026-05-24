from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.web.render import web_render
from src.core.mailer import send_email
from src.core.routes import resolve_component_slug

from .service import create_message, get_or_create_settings


async def index(request: Request, db: AsyncSession, locale: str) -> Response:
    settings = await get_or_create_settings(db)

    if request.method == "POST":
        return await _handle_post(request, db, locale, settings)

    flash = request.session.pop("flash", None)
    return await web_render(
        "com_contact/form.html",
        request=request,
        db=db,
        component="com_contact",
        locale=locale,
        flash=flash,
        settings=settings,
        errors={},
        form_data={},
    )


async def _handle_post(request, db, locale, settings) -> Response:
    form = await request.form()
    component_slug = await resolve_component_slug("com_contact", locale, db)
    redirect_url = f"/{component_slug}"

    # Honeypot: bots fill the hidden "website" field
    if form.get("website"):
        request.session["flash"] = {"type": "success", "key": "com_contact.form.sent"}
        return RedirectResponse(redirect_url, status_code=303)

    if not settings.enabled:
        request.session["flash"] = {"type": "danger", "key": "com_contact.form.disabled"}
        return RedirectResponse(redirect_url, status_code=303)

    name = str(form.get("name", "")).strip()
    email = str(form.get("email", "")).strip()
    subject = str(form.get("subject", "")).strip()
    message = str(form.get("message", "")).strip()

    errors: dict[str, str] = {}
    if not name:
        errors["name"] = "com_contact.form.error.name_required"
    if not email or "@" not in email:
        errors["email"] = "com_contact.form.error.email_invalid"
    if not message:
        errors["message"] = "com_contact.form.error.message_required"

    if errors:
        return await web_render(
            "com_contact/form.html",
            request=request,
            db=db,
            component="com_contact",
            locale=locale,
            flash=None,
            settings=settings,
            errors=errors,
            form_data={"name": name, "email": email, "subject": subject, "message": message},
        )

    client_ip = ""
    if request.client:
        client_ip = request.client.host or ""

    await create_message(
        db,
        name=name,
        email=email,
        subject=subject,
        message=message,
        ip_address=client_ip,
    )

    if settings.recipient_email:
        full_subject = f"{settings.subject_prefix} {subject}".strip()
        body_text = f"Jméno: {name}\nE-mail: {email}\n\n{message}"
        body_html = (
            f"<p><strong>Jméno:</strong> {name}<br>"
            f"<strong>E-mail:</strong> {email}</p>"
            f"<p>{message.replace(chr(10), '<br>')}</p>"
        )
        await send_email(settings.recipient_email, full_subject, body_text, body_html)

    if settings.notify_sender:
        confirm_subject = f"Potvrzení: {subject or 'zpráva přijata'}"
        confirm_text = f"Dobrý den {name},\n\nVaše zpráva byla přijata.\n\n{message}"
        confirm_html = (
            f"<p>Dobrý den {name},</p><p>Vaše zpráva byla přijata.</p>"
            f"<p><em>{message.replace(chr(10), '<br>')}</em></p>"
        )
        await send_email(email, confirm_subject, confirm_text, confirm_html)

    request.session["flash"] = {"type": "success", "key": "com_contact.form.sent"}
    return RedirectResponse(redirect_url, status_code=303)
