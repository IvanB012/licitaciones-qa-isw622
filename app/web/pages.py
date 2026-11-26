"""UI: /login, /logout y panel '/'."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_user, start_session
from app.errors import InvalidCredentials
from app.models import User
from app.services.auth import authenticate
from app.services.dashboard import get_dashboard_summary
from app.web.templating import flash, render

router = APIRouter(include_in_schema=False)


@router.get("/login")
def login_page(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"username": ""})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = authenticate(db, username, password)
    except InvalidCredentials as exc:
        return render(request, "login.html", {"username": username, "error": exc.detalle}, status_code=401)
    start_session(request, user)
    flash(request, "success", f"Bienvenido, {user.username}.")
    return RedirectResponse("/", status_code=303)


@router.api_route("/logout", methods=["GET", "POST"])
def logout(request: Request):
    request.session.clear()
    flash(request, "success", "Sesión cerrada.")
    return RedirectResponse("/login", status_code=303)


@router.get("/")
def dashboard(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return render(request, "dashboard.html", {"user": user, "summary": get_dashboard_summary(db)})
