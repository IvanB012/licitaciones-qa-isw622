"""Errores de dominio y handlers globales (contrato §4).

API (/api/*): siempre {"error": "<codigo>", "detalle": "<mensaje>"}.
UI: 401 -> redirige a /login; el resto -> página de error genérica.
Nunca se exponen trazas, rutas ni credenciales (el detalle interno solo va al log).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("licitaciones")


class DomainError(Exception):
    """Error de negocio con código estable y estado HTTP. Los services lanzan subclases/instancias."""

    status = 400
    code = "solicitud_invalida"
    default_detail = "Solicitud inválida."

    def __init__(self, detalle: str | None = None, *, code: str | None = None, status: int | None = None):
        self.detalle = detalle or self.default_detail
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
        super().__init__(self.detalle)


class BadRequest(DomainError):
    status, code, default_detail = 400, "solicitud_invalida", "Solicitud inválida."


class Unauthenticated(DomainError):
    status, code, default_detail = 401, "no_autenticado", "Debe iniciar sesión."


class InvalidCredentials(DomainError):
    status, code, default_detail = 401, "credenciales_invalidas", "Usuario o contraseña incorrectos."


class Forbidden(DomainError):
    status, code, default_detail = 403, "prohibido", "No tiene permiso para realizar esta acción."


class NotFound(DomainError):
    status, code, default_detail = 404, "no_encontrado", "El recurso solicitado no existe."


class Conflict(DomainError):
    """409. Pasar el código específico: Conflict("msg", code="duplicado")."""

    status, code, default_detail = 409, "duplicado", "Conflicto con el estado actual."


class ValidationFailed(DomainError):
    """422. Pasar el código específico: ValidationFailed("msg", code="monto_invalido")."""

    status, code, default_detail = 422, "validacion", "Los datos enviados no son válidos."


_HTTP_CODES = {
    401: ("no_autenticado", "Debe iniciar sesión."),
    403: ("prohibido", "No tiene permiso para realizar esta acción."),
    404: ("no_encontrado", "El recurso solicitado no existe."),
    405: ("metodo_no_permitido", "Método no permitido para este recurso."),
}
_GENERIC_500 = ("error_interno", "Ocurrió un error interno. Intente de nuevo más tarde.")


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api")


def _respond(request: Request, status: int, code: str, detalle: str, *, has_session: bool = True) -> Response:
    if _is_api(request):
        return JSONResponse(status_code=status, content={"error": code, "detalle": detalle})
    if status == 401:
        return RedirectResponse("/login", status_code=303)
    if has_session and "session" in request.scope and not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)  # UI sin sesión siempre va a /login
    from app.web.templating import render  # import tardío: evita ciclos

    return render(request, "error.html", {"status": status, "detalle": detalle}, status_code=status)


async def _domain_error_handler(request: Request, exc: DomainError) -> Response:
    return _respond(request, exc.status, exc.code, exc.detalle)


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> Response:
    code, detalle = _HTTP_CODES.get(exc.status_code, ("error_http", "No se pudo procesar la solicitud."))
    return _respond(request, exc.status_code, code, detalle)


def _describe(err: dict) -> str:
    loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path", "form")]
    campo = ".".join(loc) or "solicitud"
    msg = "es obligatorio" if err.get("type") == "missing" else err.get("msg", "no es válido")
    return f"{campo}: {msg}"  # nunca se incluye el valor recibido (podría ser una contraseña)


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> Response:
    errors = exc.errors()
    if any(e.get("type") == "json_invalid" for e in errors):
        return _respond(request, 400, "solicitud_invalida", "El cuerpo de la solicitud no es un JSON válido.")
    detalle = "; ".join(_describe(e) for e in errors) or "Los datos enviados no son válidos."
    return _respond(request, 422, "validacion", detalle)


async def _unhandled_handler(request: Request, exc: Exception) -> Response:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)  # solo al log
    return _respond(request, 500, *_GENERIC_500, has_session=False)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
