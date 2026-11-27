"""UI de licitaciones: /tenders, /tenders/new, /tenders/{id}, /tenders/{id}/edit y acciones. Usa los mismos services que la API."""
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.errors import DomainError, ValidationFailed
from app.models import Tender
from app.rules.constants import STATUS_BORRADOR, TENDER_STATUSES
from app.rules.money import format_money
from app.rules.tenders import is_expired
from app.rules.timeutil import from_cr, to_cr
from app.services import evaluation as evaluation_service
from app.services import offers as offers_service
from app.services import tenders as service
from app.services.currency import current_rate
from app.web.templating import flash, get_currency, render

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_user)])

FORM_DT = "%Y-%m-%dT%H:%M"  # valor de <input type="datetime-local">


def _parse_closes_at(text: str) -> datetime:
    """Lo escrito en el formulario es hora de Costa Rica; se guarda en UTC."""
    try:
        return from_cr(datetime.fromisoformat(text.strip()))
    except ValueError:
        raise ValidationFailed("La fecha y hora de cierre no son válidas.", code="validacion") from None


def _view_ctx(db: Session, clock: Clock) -> dict:
    now = clock.now()
    return {"rate": current_rate(db, clock), "now": now, "is_expired": lambda t: is_expired(t.status, t.closes_at, now)}


def _form_values(tender: Tender | None) -> dict:
    if tender is None:
        return {"code": "", "title": "", "description": "", "budget": "", "closes_at": ""}
    return {
        "code": tender.code,
        "title": tender.title,
        "description": tender.description or "",
        "budget": format_money(tender.budget_cents),
        "closes_at": to_cr(tender.closes_at).strftime(FORM_DT),
    }


def _render_form(request: Request, *, tender: Tender | None, form: dict, error: str | None = None, status_code: int = 200):
    return render(
        request, "tenders/form.html", {"tender": tender, "form": form, "error": error}, status_code=status_code
    )


@router.get("/tenders")
def tenders_list(
    request: Request, status: str = "", db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
):
    tenders = service.list_tenders(db, status or None)
    ctx = {"tenders": tenders, "statuses": TENDER_STATUSES, "status_filter": status, **_view_ctx(db, clock)}
    return render(request, "tenders/list.html", ctx)


@router.get("/tenders/new")
def tender_new_page(request: Request):
    return _render_form(request, tender=None, form=_form_values(None))


@router.post("/tenders/new")
def tender_new_submit(
    request: Request,
    code: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    budget: str = Form(""),
    closes_at: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    form = {"code": code, "title": title, "description": description, "budget": budget, "closes_at": closes_at}
    try:
        tender = service.create_tender(
            db, clock, code=code, title=title, description=description, budget=budget,
            closes_at=_parse_closes_at(closes_at),
        )
    except DomainError as exc:
        return _render_form(request, tender=None, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Licitación {tender.code} creada en estado Borrador.")
    return RedirectResponse(f"/tenders/{tender.id}", status_code=303)


def render_tender_detail(
    request: Request,
    db: Session,
    clock: Clock,
    tender: Tender,
    *,
    offer_form: dict | None = None,
    offer_error: str | None = None,
    status_code: int = 200,
):
    """Detalle de la licitación con su sección de ofertas (la reutiliza web/offers.py para mostrar errores)."""
    ctx = {
        "tender": tender,
        "evaluation": evaluation_service.evaluate(db, clock, tender.id, get_currency(request), strict=False),
        "offers": offers_service.list_offers(db, tender.id),
        "providers": offers_service.list_provider_options(db),
        "offer_form": offer_form or {"provider_id": "", "amount": ""},
        "offer_error": offer_error,
        **_view_ctx(db, clock),
    }
    return render(request, "tenders/detail.html", ctx, status_code=status_code)


@router.get("/tenders/{tender_id}")
def tender_detail(
    request: Request, tender_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
):
    return render_tender_detail(request, db, clock, service.get_tender(db, tender_id))


@router.get("/tenders/{tender_id}/edit")
def tender_edit_page(request: Request, tender_id: int, db: Session = Depends(get_db)):
    tender = service.get_tender(db, tender_id)
    if tender.status != STATUS_BORRADOR:
        flash(request, "error", "Solo se puede editar una licitación en estado Borrador.")
        return RedirectResponse(f"/tenders/{tender.id}", status_code=303)
    return _render_form(request, tender=tender, form=_form_values(tender))


@router.post("/tenders/{tender_id}/edit")
def tender_edit_submit(
    request: Request,
    tender_id: int,
    code: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    budget: str = Form(""),
    closes_at: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    tender = service.get_tender(db, tender_id)
    form = {"code": code, "title": title, "description": description, "budget": budget, "closes_at": closes_at}
    try:
        tender = service.update_tender(
            db, clock, tender_id, code=code, title=title, description=description, budget=budget,
            closes_at=_parse_closes_at(closes_at),
        )
    except DomainError as exc:
        return _render_form(request, tender=tender, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Licitación {tender.code} actualizada.")
    return RedirectResponse(f"/tenders/{tender.id}", status_code=303)


def _action(request: Request, tender_id: int, run, ok_message: str, redirect_to: str | None = None):
    """Ejecuta una acción (publicar/cerrar/borrar). Si el service la rechaza, muestra el mismo `detalle` que la API."""
    try:
        run()
    except DomainError as exc:
        flash(request, "error", exc.detalle)
        return RedirectResponse(f"/tenders/{tender_id}", status_code=303)
    flash(request, "success", ok_message)
    return RedirectResponse(redirect_to or f"/tenders/{tender_id}", status_code=303)


@router.post("/tenders/{tender_id}/publish")
def tender_publish(request: Request, tender_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return _action(request, tender_id, lambda: service.publish_tender(db, clock, tender_id), "Licitación publicada.")


@router.post("/tenders/{tender_id}/close")
def tender_close(request: Request, tender_id: int, db: Session = Depends(get_db)):
    return _action(request, tender_id, lambda: service.close_tender(db, tender_id), "Licitación cerrada.")


@router.post("/tenders/{tender_id}/delete")
def tender_delete(request: Request, tender_id: int, db: Session = Depends(get_db)):
    return _action(
        request, tender_id, lambda: service.delete_tender(db, tender_id), "Licitación eliminada.", "/tenders"
    )
