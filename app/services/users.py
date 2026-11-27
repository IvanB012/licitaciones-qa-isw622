"""Casos de uso de usuarios (solo rol admin; contrato §5 Usuarios). Los usan la API y la UI.

Las contraseñas solo se guardan con hash (argon2) y nunca se devuelven. El nombre de usuario es único sin distinguir
mayúsculas (la BD lo respalda con un índice sobre lower(username)).
"""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import Conflict, NotFound
from app.models import User
from app.rules import users as rules
from app.rules.constants import ROLE_ADMIN
from app.security import hash_password

DUPLICATE_MSG = "Ya existe un usuario con ese nombre."
SELF_MSG = "No puede {} su propio usuario."


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("El usuario no existe.")
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(func.lower(User.username), User.id)))


def _username_taken(db: Session, username: str) -> bool:
    return db.scalar(select(User.id).where(func.lower(User.username) == username.casefold())) is not None


def create_user(db: Session, *, username: object, password: object, role: object) -> User:
    clean = rules.clean_username(username)
    secret = rules.validate_password(password)
    level = rules.validate_role(role)
    if _username_taken(db, clean):
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    user = User(username=clean, password_hash=hash_password(secret), role=level, active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # índice único lower(username): mismo error que el chequeo previo
        db.rollback()
        raise Conflict(DUPLICATE_MSG, code="duplicado") from None
    return user


def update_user(
    db: Session, user_id: int, actor_id: int, *, role: object = None, active: object = None, password: object = None
) -> User:
    """Cambia rol, estado y/o contraseña. ``None`` = no cambiar ese campo. El usuario no se renombra.

    Un admin no puede quitarse el rol ni desactivarse a sí mismo (evita quedarse sin acceso).
    """
    user = get_user(db, user_id)
    new_role = rules.validate_role(role) if role is not None else None
    new_active = rules.validate_active(active) if active is not None else None
    new_password = rules.validate_password(password) if password is not None else None

    if user.id == actor_id:
        if new_role is not None and new_role != ROLE_ADMIN:
            raise Conflict(SELF_MSG.format("quitarse el rol de administrador en"), code="en_uso")
        if new_active is False:
            raise Conflict(SELF_MSG.format("desactivar"), code="en_uso")

    if new_role is not None:
        user.role = new_role
    if new_active is not None:
        user.active = new_active
    if new_password is not None:
        user.password_hash = hash_password(new_password)
    db.commit()
    return user


def delete_user(db: Session, user_id: int, actor_id: int) -> None:
    user = get_user(db, user_id)
    if user.id == actor_id:
        raise Conflict(SELF_MSG.format("borrar"), code="en_uso")
    db.delete(user)
    db.commit()
