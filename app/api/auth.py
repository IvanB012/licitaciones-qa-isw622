"""POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me (contrato §5 Auth)."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db, require_user, start_session
from app.models import User
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class SessionUserOut(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=SessionUserOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = authenticate(db, data.username, data.password)  # 401 credenciales_invalidas
    start_session(request, user)
    return SessionUserOut(username=user.username, role=user.role)


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=SessionUserOut)
def me(user: User = Depends(require_user)):
    return SessionUserOut(username=user.username, role=user.role)
