"""UI de rangos de aprobación (solo admin): /approval-ranges, /new, /{id}/edit y borrar. Mismos services que la API."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.errors import DomainError
from app.models import ApprovalRange
from app.rules.constants import APPROVAL_LEVELS
from app.rules.money import format_money
from app.services import approval_ranges as service
from app.web.templating import flash, render

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_admin)])


def _form_values(row: ApprovalRange | None) -> dict:
    if row is None:
        return {"level": "", "min": "", "max": ""}
    return {
        "level": row.level,
        "min": format_money(row.min_cents),
        "max": "" if row.max_cents is None else format_money(row.max_cents),
    }


def _render_form(request: Request, *, row: ApprovalRange | None, form: dict, error: str | None = None, status_code: int = 200):
    ctx = {"range_row": row, "form": form, "error": error, "levels": APPROVAL_LEVELS}
    return render(request, "approval_ranges/form.html", ctx, status_code=status_code)


@router.get("/approval-ranges")
def ranges_list(request: Request, db: Session = Depends(get_db)):
    return render(request, "approval_ranges/list.html", {"ranges": service.list_ranges(db)})


@router.get("/approval-ranges/new")
def range_new_page(request: Request):
    return _render_form(request, row=None, form=_form_values(None))


@router.post("/approval-ranges/new")
def range_new_submit(
    request: Request,
    level: str = Form(""),
    min: str = Form(""),
    max: str = Form(""),
    db: Session = Depends(get_db),
):
    form = {"level": level, "min": min, "max": max}
    try:
        row = service.create_range(db, level=level, min=min, max=max)
    except DomainError as exc:
        return _render_form(request, row=None, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Rango de {row.level} creado.")
    return RedirectResponse("/approval-ranges", status_code=303)


@router.get("/approval-ranges/{range_id}/edit")
def range_edit_page(request: Request, range_id: int, db: Session = Depends(get_db)):
    row = service.get_range(db, range_id)
    return _render_form(request, row=row, form=_form_values(row))


@router.post("/approval-ranges/{range_id}/edit")
def range_edit_submit(
    request: Request,
    range_id: int,
    level: str = Form(""),
    min: str = Form(""),
    max: str = Form(""),
    db: Session = Depends(get_db),
):
    row = service.get_range(db, range_id)
    form = {"level": level, "min": min, "max": max}
    try:
        row = service.update_range(db, range_id, level=level, min=min, max=max)
    except DomainError as exc:
        return _render_form(request, row=row, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Rango de {row.level} actualizado.")
    return RedirectResponse("/approval-ranges", status_code=303)


@router.post("/approval-ranges/{range_id}/delete")
def range_delete(request: Request, range_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_range(db, range_id)
    except DomainError as exc:
        flash(request, "error", exc.detalle)
        return RedirectResponse("/approval-ranges", status_code=303)
    flash(request, "success", "Rango eliminado.")
    return RedirectResponse("/approval-ranges", status_code=303)
