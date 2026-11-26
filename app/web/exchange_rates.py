"""UI de tipo de cambio: /exchange-rates (vigente + listado), alta, edición, borrado y "Sugerir tasa" (sin JavaScript)."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, get_rate_provider, require_user
from app.errors import DomainError
from app.exchange import ExchangeRateProvider
from app.models import ExchangeRate
from app.rules.constants import RATE_SOURCE_MANUAL, RATE_SOURCE_SUGERIDA
from app.rules.timeutil import official_date
from app.services import exchange_rates as service
from app.services.currency import current_rate
from app.web.templating import flash, render

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_user)])


def _render_form(
    request: Request, *, rate_row: ExchangeRate | None, form: dict, error: str | None = None,
    notice: str | None = None, status_code: int = 200,
):
    ctx = {"rate_row": rate_row, "form": form, "error": error, "notice": notice}
    return render(request, "exchange_rates/form.html", ctx, status_code=status_code)


def _new_form(clock: Clock, rate: str = "", source: str = RATE_SOURCE_MANUAL) -> dict:
    return {"rate": rate, "rate_date": official_date(clock.now()).isoformat(), "source": source}


@router.get("/exchange-rates")
def rates_list(request: Request, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    ctx = {"rates": service.list_rates(db), "current": current_rate(db, clock), "rate_text": service.rate_text}
    return render(request, "exchange_rates/list.html", ctx)


@router.get("/exchange-rates/new")
def rate_new_page(request: Request, clock: Clock = Depends(get_clock)):
    return _render_form(request, rate_row=None, form=_new_form(clock))


@router.post("/exchange-rates/new")
def rate_new_submit(
    request: Request,
    rate: str = Form(""),
    rate_date: str = Form(""),
    source: str = Form(RATE_SOURCE_MANUAL),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    form = {"rate": rate, "rate_date": rate_date, "source": source}
    try:
        row = service.create_rate(db, clock, rate=rate, rate_date=rate_date, source=source)
    except DomainError as exc:
        return _render_form(request, rate_row=None, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Tipo de cambio ₡{service.rate_text(row)} por USD guardado.")
    return RedirectResponse("/exchange-rates", status_code=303)


@router.post("/exchange-rates/suggest")
def rate_suggest(
    request: Request,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
    provider: ExchangeRateProvider = Depends(get_rate_provider),
):
    """Solo rellena el formulario (no guarda). El usuario confirma con 'Guardar'."""
    result = service.suggest(db, clock, provider)
    if result["source"] == service.SOURCE_RESPALDO:
        return _render_form(
            request, rate_row=None, form=_new_form(clock, result["rate"], RATE_SOURCE_MANUAL), notice=result["aviso"]
        )
    return _render_form(request, rate_row=None, form=_new_form(clock, result["rate"], RATE_SOURCE_SUGERIDA))


@router.get("/exchange-rates/{rate_id}/edit")
def rate_edit_page(request: Request, rate_id: int, db: Session = Depends(get_db)):
    row = service.get_rate(db, rate_id)
    form = {"rate": service.rate_text(row), "rate_date": row.rate_date.isoformat(), "source": row.source}
    return _render_form(request, rate_row=row, form=form)


@router.post("/exchange-rates/{rate_id}/edit")
def rate_edit_submit(
    request: Request,
    rate_id: int,
    rate: str = Form(""),
    rate_date: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    row = service.get_rate(db, rate_id)
    form = {"rate": rate, "rate_date": rate_date, "source": row.source}
    try:
        row = service.update_rate(db, clock, rate_id, rate=rate, rate_date=rate_date or None)
    except DomainError as exc:
        return _render_form(request, rate_row=row, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", "Tipo de cambio actualizado.")
    return RedirectResponse("/exchange-rates", status_code=303)


@router.post("/exchange-rates/{rate_id}/delete")
def rate_delete(request: Request, rate_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_rate(db, rate_id)
    except DomainError as exc:
        flash(request, "error", exc.detalle)
        return RedirectResponse("/exchange-rates", status_code=303)
    flash(request, "success", "Tipo de cambio eliminado.")
    return RedirectResponse("/exchange-rates", status_code=303)
