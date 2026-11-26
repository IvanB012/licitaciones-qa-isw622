"""Dependencias FastAPI compartidas por API y UI.

Uso en un router:  db: Session = Depends(get_db);  user: User = Depends(require_user)
Los services hacen commit; get_db solo cierra la sesión.
"""
from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.clock import get_clock  # noqa: F401  (re-export)
from app.errors import Forbidden, Unauthenticated
from app.exchange import get_rate_provider  # noqa: F401  (re-export)
from app.models import User
from app.rules.constants import ROLE_ADMIN


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Usuario de la sesión o None. Invalida la sesión si el usuario ya no existe o está inactivo."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.active:
        request.session.clear()
        return None
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    """401 en la API; en la UI el handler redirige a /login."""
    if user is None:
        raise Unauthenticated()
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise Forbidden()
    return user


def start_session(request: Request, user: User) -> None:
    """Abre sesión (cookie firmada). Limpia antes para evitar fijación de sesión."""
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
