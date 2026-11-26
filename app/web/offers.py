"""UI de ofertas: alta desde el detalle de la licitación, edición y borrado. Usa los mismos services que la API."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.errors import DomainError
from app.rules.money import format_money
from app.services import offers as service
from app.services import tenders as tenders_service
from app.web.templating import flash, render
from app.web.tenders import render_tender_detail

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_user)])


@router.post("/tenders/{tender_id}/offers")
def offer_create(
    request: Request,
    tender_id: int,
    provider_id: str = Form(""),
    amount: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    tender = tenders_service.get_tender(db, tender_id)
    form = {"provider_id": provider_id, "amount": amount}
    try:
        if not provider_id.strip().isdigit():
            raise DomainError("Seleccione un proveedor.", code="validacion", status=422)
        offer = service.create_offer(db, clock, tender_id, int(provider_id), amount)
    except DomainError as exc:
        return render_tender_detail(
            request, db, clock, tender, offer_form=form, offer_error=exc.detalle, status_code=exc.status
        )
    flash(request, "success", f"Oferta de {offer.provider.name} registrada.")
    return RedirectResponse(f"/tenders/{tender_id}", status_code=303)


@router.get("/offers/{offer_id}/edit")
def offer_edit_page(request: Request, offer_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    offer = service.get_offer(db, offer_id)
    return render(
        request, "offers/form.html", {"offer": offer, "form": {"amount": format_money(offer.amount_cents)}, "error": None}
    )


@router.post("/offers/{offer_id}/edit")
def offer_edit_submit(
    request: Request,
    offer_id: int,
    amount: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    offer = service.get_offer(db, offer_id)
    try:
        service.update_offer(db, clock, offer_id, amount)
    except DomainError as exc:
        return render(
            request, "offers/form.html", {"offer": offer, "form": {"amount": amount}, "error": exc.detalle},
            status_code=exc.status,
        )
    flash(request, "success", "Oferta actualizada.")
    return RedirectResponse(f"/tenders/{offer.tender_id}", status_code=303)


@router.post("/offers/{offer_id}/delete")
def offer_delete(request: Request, offer_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    offer = service.get_offer(db, offer_id)
    tender_id = offer.tender_id
    try:
        service.delete_offer(db, clock, offer_id)
    except DomainError as exc:
        flash(request, "error", exc.detalle)
    else:
        flash(request, "success", "Oferta eliminada.")
    return RedirectResponse(f"/tenders/{tender_id}", status_code=303)
