from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.registry import ComponentRegistry

_COMPONENT_DIR = Path(__file__).parent


def setup(reg: "ComponentRegistry") -> None:
    from src.components.com_contact import admin, web_views
    from src.core.templates import get_frontend_env
    from src.i18n.translator import translator
    from jinja2 import FileSystemLoader

    reg.register("com_contact", "src.components.com_contact")
    reg.register_display_name("com_contact", "components.name.com_contact")
    reg.register_admin_url("com_contact", "/admin/com_contact")
    reg.register_web_view("com_contact", "index", web_views.index)
    reg.register_router(admin.router)

    translator.load_domain("com_contact", _COMPONENT_DIR / "i18n")

    # Frontend templates are not auto-scanned for external components
    templates_dir = _COMPONENT_DIR / "templates"
    if templates_dir.is_dir():
        for env in (get_frontend_env("default"),):
            loaders = getattr(env.loader, "loaders", [])
            if not any(
                isinstance(ldr, FileSystemLoader) and str(templates_dir) in ldr.searchpath
                for ldr in loaders
            ):
                loaders.append(FileSystemLoader(str(templates_dir)))
