"""Jinja2 (autoescape activo) y helpers de render/flash/moneda de la UI."""
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.rules.constants import CURRENCIES
from app.rules.timeutil import to_cr

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))  # autoescape=True por defecto: NO usar |safe con datos de usuario


def cr_datetime(value, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Filtro: instante UTC -> hora de Costa Rica (UTC−6) para mostrar."""
    return "" if value is None else to_cr(value).strftime(fmt)


templates.env.filters["cr_datetime"] = cr_datetime


def flash(request: Request, category: str, message: str) -> None:
    """Mensaje para la próxima página. category: success | error | info | warning."""
    request.session.setdefault("_flashes", []).append([category, message])


def get_currency(request: Request) -> str:
    """Moneda de VISTA (CRC|USD): ?currency=... o la última elegida. No toca la BD (REQ-010)."""
    if "session" not in request.scope:
        return "CRC"
    wanted = request.query_params.get("currency", "").upper()
    if wanted in CURRENCIES:
        request.session["currency"] = wanted
        return wanted
    current = request.session.get("currency", "CRC")
    return current if current in CURRENCIES else "CRC"


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    has_session = "session" in request.scope
    session = request.session if has_session else {}
    current_user = (
        {"username": session.get("username"), "role": session.get("role")} if session.get("user_id") else None
    )
    ctx = {
        "current_user": current_user,
        "flashes": request.session.pop("_flashes", []) if has_session else [],
        "currency": get_currency(request),
    }
    ctx.update(context or {})
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
