"""Casos de uso de autenticación (compartido por API y UI)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import InvalidCredentials
from app.models import User
from app.security import DUMMY_HASH, verify_password


def authenticate(db: Session, username: str, password: str) -> User:
    """Devuelve el usuario activo o lanza InvalidCredentials (mismo error si no existe, está inactivo o la clave falla)."""
    key = (username or "").strip().casefold()
    user = db.scalar(select(User).where(func.lower(User.username) == key))
    if user is None:
        verify_password(DUMMY_HASH, password or "")  # igualar tiempos
        raise InvalidCredentials()
    if not verify_password(user.password_hash, password or "") or not user.active:
        raise InvalidCredentials()
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
