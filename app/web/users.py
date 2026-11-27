"""UI de usuarios (solo admin): /users, /users/new, /users/{id}/edit y borrar. Usa los mismos services que la API."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.errors import DomainError
from app.models import User
from app.rules.constants import ROLES
from app.services import users as service
from app.web.templating import flash, render

router = APIRouter(include_in_schema=False)


def _form_values(user: User | None) -> dict:
    if user is None:
        return {"username": "", "role": "operador", "active": True}
    return {"username": user.username, "role": user.role, "active": user.active}


def _render_form(request: Request, *, user: User | None, form: dict, error: str | None = None, status_code: int = 200):
    # La contraseña nunca se vuelve a mostrar en el formulario.
    return render(
        request, "users/form.html", {"user_obj": user, "form": form, "roles": ROLES, "error": error}, status_code=status_code
    )


@router.get("/users")
def users_list(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return render(request, "users/list.html", {"users": service.list_users(db), "me_id": admin.id})


@router.get("/users/new")
def user_new_page(request: Request, _: User = Depends(require_admin)):
    return _render_form(request, user=None, form=_form_values(None))


@router.post("/users/new")
def user_new_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    role: str = Form(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    form = {"username": username, "role": role, "active": True}
    try:
        user = service.create_user(db, username=username, password=password, role=role)
    except DomainError as exc:
        return _render_form(request, user=None, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Usuario {user.username} creado.")
    return RedirectResponse("/users", status_code=303)


@router.get("/users/{user_id}/edit")
def user_edit_page(request: Request, user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = service.get_user(db, user_id)
    return _render_form(request, user=user, form=_form_values(user))


@router.post("/users/{user_id}/edit")
def user_edit_submit(
    request: Request,
    user_id: int,
    role: str = Form(""),
    active: str = Form(""),  # casilla: "on" si está marcada, ausente si no
    password: str = Form(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = service.get_user(db, user_id)
    is_active = active == "on"
    form = {"username": user.username, "role": role, "active": is_active}
    try:
        # Contraseña vacía = no cambiarla
        user = service.update_user(db, user_id, admin.id, role=role, active=is_active, password=password or None)
    except DomainError as exc:
        return _render_form(request, user=user, form=form, error=exc.detalle, status_code=exc.status)
    flash(request, "success", f"Usuario {user.username} actualizado.")
    return RedirectResponse("/users", status_code=303)


@router.post("/users/{user_id}/delete")
def user_delete(request: Request, user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        service.delete_user(db, user_id, admin.id)
    except DomainError as exc:
        flash(request, "error", exc.detalle)  # 404 o en_uso: mismo detalle que la API
        return RedirectResponse("/users", status_code=303)
    flash(request, "success", "Usuario eliminado.")
    return RedirectResponse("/users", status_code=303)
