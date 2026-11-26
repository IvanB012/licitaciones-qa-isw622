"""UI de proveedores: /providers, /providers/new, /providers/{id}/edit y borrar. Usa los mismos services que la API."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.errors import DomainError
from app.models import Provider
from app.services import providers as service
from app.web.templating import flash, render

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_user)])


def _form_values(provider: Provider | None) -> dict:
    if provider is None:
        return {"name": "", "contact_email": ""}
    return {"name": provider.name, "contact_email": provider.contact_email or ""}


def _render_form(request: Request, *, provider: Provider | None, form: dict, error: str | None = None, status_code: int = 200):
    return render(
        request, "providers/form.html", {"provider": provider, "form": form, "error": error}, status_code=status_code
    )


@router.get("/providers")
def providers_list(request: Request, db: Session = Depends(get_db)):
    return render(request, "providers/list.html", {"providers": service.list_providers(db)})


@router.get("/providers/new")
def provider_new_page(request: Request):
    return _render_form(request, provider=None, form=_form_values(None))


@router.post("/providers/new")
def provider_new_submit(
    request: Request,
    name: str = Form(""),
    contact_email: str = Form(""),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    form = {"name": name, "contact_email": contact_email}
    try:
        provider = service.create_provider(db, clock, name=name, contact_email=contact_email)
    except DomainError as exc:
        return _render_form(request, provider=None, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Proveedor {provider.name} creado.")
    return RedirectResponse("/providers", status_code=303)


@router.get("/providers/{provider_id}/edit")
def provider_edit_page(request: Request, provider_id: int, db: Session = Depends(get_db)):
    provider = service.get_provider(db, provider_id)
    return _render_form(request, provider=provider, form=_form_values(provider))


@router.post("/providers/{provider_id}/edit")
def provider_edit_submit(
    request: Request,
    provider_id: int,
    name: str = Form(""),
    contact_email: str = Form(""),
    db: Session = Depends(get_db),
):
    provider = service.get_provider(db, provider_id)
    form = {"name": name, "contact_email": contact_email}
    try:
        provider = service.update_provider(db, provider_id, name=name, contact_email=contact_email)
    except DomainError as exc:
        return _render_form(request, provider=provider, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Proveedor {provider.name} actualizado.")
    return RedirectResponse("/providers", status_code=303)


@router.post("/providers/{provider_id}/delete")
def provider_delete(request: Request, provider_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_provider(db, provider_id)
    except DomainError as exc:
        flash(request, "error", exc.detalle)  # 404 o en_uso: mismo detalle que la API
        return RedirectResponse("/providers", status_code=303)
    flash(request, "success", "Proveedor eliminado.")
    return RedirectResponse("/providers", status_code=303)
