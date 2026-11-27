"""Rutas de usuarios (contrato §5; solo admin). Delgadas: la lógica está en app/services/users.py."""
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import User
from app.services import users as service

router = APIRouter(prefix="/users", tags=["users"])


class UserIn(BaseModel):
    # Any: el formato lo valida el service (mismos errores que la UI).
    username: Any
    password: Any
    role: Any


class UserUpdate(BaseModel):
    role: Any = None
    active: Any = None
    password: Any = None


def user_out(u: User) -> dict:
    """Nunca incluye la contraseña ni su hash."""
    return {"id": u.id, "username": u.username, "role": u.role, "active": u.active}


@router.post("", status_code=201)
def create_user(data: UserIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return user_out(service.create_user(db, **data.model_dump()))


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [user_out(u) for u in service.list_users(db)]


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return user_out(service.get_user(db, user_id))


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return user_out(service.update_user(db, user_id, admin.id, **data.model_dump()))


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> Response:
    service.delete_user(db, user_id, admin.id)
    return Response(status_code=204)
