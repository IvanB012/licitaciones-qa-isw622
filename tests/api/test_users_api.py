"""API de usuarios (contrato §5 Usuarios y §8). Solo admin; nunca devuelve contraseñas ni hashes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app.models import User
from tests.conftest import ADMIN, OPERADOR

NUEVO = {"username": "ana.mora", "password": "Clave#2026-ok", "role": "operador"}


@pytest.fixture
def adm(client, seeded, login):
    assert login(*ADMIN).status_code == 200
    return client


def _otra_sesion(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _puede_entrar(app, usuario, clave) -> bool:
    with _otra_sesion(app) as c:
        return c.post("/api/auth/login", json={"username": usuario, "password": clave}).status_code == 200


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


def _crear(adm, **over):
    return adm.post("/api/users", json={**NUEVO, **over})


# ---- acceso: solo admin ----
RUTAS = [
    ("get", "/api/users", None),
    ("post", "/api/users", NUEVO),
    ("get", "/api/users/1", None),
    ("put", "/api/users/1", {"role": "operador"}),
    ("delete", "/api/users/1", None),
]


@pytest.mark.parametrize("metodo, ruta, cuerpo", RUTAS)
def test_sin_sesion_401(client, seeded, metodo, ruta, cuerpo):
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    _error(r, 401, "no_autenticado")


@pytest.mark.parametrize("metodo, ruta, cuerpo", RUTAS)
def test_operador_no_puede_gestionar_usuarios_403(client, seeded, login, metodo, ruta, cuerpo):
    login(*OPERADOR)
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    _error(r, 403, "prohibido")


def test_operador_no_crea_usuarios_aunque_lo_intente(client, seeded, login, db):
    login(*OPERADOR)
    client.post("/api/users", json=NUEVO)
    assert db.scalar(select(func.count()).select_from(User)) == 2  # sigue habiendo solo los del seed


# ---- crear ----
def test_crear_usuario_valido(adm, db):
    r = _crear(adm)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "username", "role", "active"}
    assert (body["username"], body["role"], body["active"]) == ("ana.mora", "operador", True)
    assert adm.get(f"/api/users/{body['id']}").json() == body


def test_la_respuesta_nunca_incluye_clave_ni_hash(adm):
    texto = _crear(adm).text.lower()
    for prohibido in ("password", "hash", "argon2", "clave#2026"):
        assert prohibido not in texto


def test_la_contrasena_se_guarda_solo_con_hash(adm, db):
    uid = _crear(adm).json()["id"]
    db.expire_all()
    guardado = db.get(User, uid).password_hash
    assert guardado.startswith("$argon2") and "Clave#2026-ok" not in guardado


def test_el_usuario_creado_puede_iniciar_sesion(adm, app):
    _crear(adm)
    assert _puede_entrar(app, "ana.mora", "Clave#2026-ok")
    assert _puede_entrar(app, "  ANA.MORA ", "Clave#2026-ok")  # el login no distingue mayúsculas
    assert not _puede_entrar(app, "ana.mora", "otra-clave-123")


def test_se_conserva_la_capitalizacion_escrita(adm):
    assert _crear(adm, username="Ana.Mora").json()["username"] == "Ana.Mora"


def test_se_puede_crear_otro_admin(adm):
    assert _crear(adm, username="segundo.admin", role="admin").json()["role"] == "admin"


@pytest.mark.parametrize("usuario", ["admin", "ADMIN", "Operador", " operador ", "OpErAdOr"])
def test_usuario_duplicado_sin_distinguir_mayusculas_409(adm, usuario):
    _error(_crear(adm, username=usuario), 409, "duplicado")


def test_el_duplicado_no_crea_registros(adm, db):
    _crear(adm, username="ADMIN")
    assert db.scalar(select(func.count()).select_from(User)) == 2


@pytest.mark.parametrize("usuario", ["", "   ", "ab", "a" * 51, "con espacio", "x<script>", "ñandú", 123, None])
def test_usuario_invalido_422(adm, usuario):
    _error(_crear(adm, username=usuario), 422, "validacion_usuario")


@pytest.mark.parametrize("clave", ["", "corta", "1234567", "a" * 129, 12345678, None])
def test_contrasena_invalida_422(adm, clave):
    _error(_crear(adm, password=clave), 422, "validacion_clave")


@pytest.mark.parametrize("rol", ["superuser", "ADMIN", "", None, 1])
def test_rol_invalido_422(adm, rol):
    _error(_crear(adm, role=rol), 422, "validacion_rol")


def test_el_error_de_contrasena_no_repite_la_clave_enviada(adm):
    r = _crear(adm, password="Corta1")
    assert r.status_code == 422 and "Corta1" not in r.text


def test_campos_faltantes_422(adm):
    r = adm.post("/api/users", json={"username": "solo.usuario"})
    assert r.status_code == 422 and r.json()["error"] == "validacion"
    assert "Corta1" not in r.text


def test_json_malformado_400(adm):
    r = adm.post("/api/users", content="{no es json", headers={"content-type": "application/json"})
    _error(r, 400, "solicitud_invalida")


# ---- consultar ----
def test_listar_usuarios_sin_hashes(adm, seeded):
    lista = adm.get("/api/users").json()
    assert [(u["username"], u["role"], u["active"]) for u in lista] == [
        ("admin", "admin", True), ("operador", "operador", True),
    ]
    assert all(set(u) == {"id", "username", "role", "active"} for u in lista)
    assert "argon2" not in adm.get("/api/users").text


def test_obtener_inexistente_404(adm):
    _error(adm.get("/api/users/9999"), 404, "no_encontrado")


# ---- editar ----
def test_cambiar_rol(adm, seeded):
    r = adm.put(f"/api/users/{seeded.operador_id}", json={"role": "admin"})
    assert r.status_code == 200 and r.json()["role"] == "admin"


def test_desactivar_impide_iniciar_sesion(adm, seeded, app):
    r = adm.put(f"/api/users/{seeded.operador_id}", json={"active": False})
    assert r.json()["active"] is False
    assert not _puede_entrar(app, *OPERADOR)


def test_desactivar_invalida_la_sesion_abierta(adm, seeded, app):
    with _otra_sesion(app) as otro:
        otro.post("/api/auth/login", json={"username": OPERADOR[0], "password": OPERADOR[1]})
        assert otro.get("/api/auth/me").status_code == 200
        adm.put(f"/api/users/{seeded.operador_id}", json={"active": False})
        assert otro.get("/api/auth/me").status_code == 401


def test_reactivar_permite_volver_a_entrar(adm, seeded, app):
    adm.put(f"/api/users/{seeded.operador_id}", json={"active": False})
    adm.put(f"/api/users/{seeded.operador_id}", json={"active": True})
    assert _puede_entrar(app, *OPERADOR)


def test_cambiar_contrasena(adm, seeded, app, db):
    antes = db.get(User, seeded.operador_id).password_hash
    adm.put(f"/api/users/{seeded.operador_id}", json={"password": "Nueva#Clave-2026"})
    db.expire_all()
    assert db.get(User, seeded.operador_id).password_hash != antes
    assert _puede_entrar(app, OPERADOR[0], "Nueva#Clave-2026")
    assert not _puede_entrar(app, *OPERADOR)  # la anterior ya no sirve


def test_cuerpo_vacio_no_cambia_nada(adm, seeded):
    r = adm.put(f"/api/users/{seeded.operador_id}", json={})
    assert r.status_code == 200 and (r.json()["role"], r.json()["active"]) == ("operador", True)


@pytest.mark.parametrize(
    "cuerpo, codigo",
    [
        ({"role": "superuser"}, "validacion_rol"),
        ({"active": "si"}, "validacion_activo"),
        ({"active": 1}, "validacion_activo"),
        ({"password": "corta"}, "validacion_clave"),
        ({"password": ""}, "validacion_clave"),
    ],
)
def test_actualizacion_invalida_422(adm, seeded, cuerpo, codigo):
    _error(adm.put(f"/api/users/{seeded.operador_id}", json=cuerpo), 422, codigo)


def test_una_actualizacion_invalida_no_aplica_cambios_parciales(adm, seeded, db):
    adm.put(f"/api/users/{seeded.operador_id}", json={"role": "admin", "password": "corta"})
    db.expire_all()
    assert db.get(User, seeded.operador_id).role == "operador"  # ni el rol válido se aplicó


def test_el_nombre_de_usuario_no_se_puede_cambiar(adm, seeded):
    r = adm.put(f"/api/users/{seeded.operador_id}", json={"username": "otro.nombre"})
    assert r.status_code == 200 and r.json()["username"] == "operador"


def test_editar_inexistente_404(adm):
    _error(adm.put("/api/users/9999", json={"role": "admin"}), 404, "no_encontrado")


# ---- el admin no puede dejarse sin acceso ----
def test_no_puede_quitarse_el_rol_admin(adm, seeded, db):
    _error(adm.put(f"/api/users/{seeded.admin_id}", json={"role": "operador"}), 409, "en_uso")
    db.expire_all()
    assert db.get(User, seeded.admin_id).role == "admin"


def test_no_puede_desactivarse_a_si_mismo(adm, seeded, db):
    _error(adm.put(f"/api/users/{seeded.admin_id}", json={"active": False}), 409, "en_uso")
    db.expire_all()
    assert db.get(User, seeded.admin_id).active is True
    assert adm.get("/api/auth/me").status_code == 200


def test_si_puede_cambiar_su_propia_contrasena_y_conservar_su_rol(adm, seeded, app):
    r = adm.put(f"/api/users/{seeded.admin_id}", json={"role": "admin", "active": True, "password": "Otra#Clave-2026"})
    assert r.status_code == 200
    assert _puede_entrar(app, "admin", "Otra#Clave-2026")


# ---- borrar ----
def test_borrar_otro_usuario(adm, seeded, app):
    assert adm.delete(f"/api/users/{seeded.operador_id}").status_code == 204
    _error(adm.get(f"/api/users/{seeded.operador_id}"), 404, "no_encontrado")
    assert not _puede_entrar(app, *OPERADOR)


def test_borrar_y_volver_a_crear_el_mismo_usuario(adm, seeded):
    adm.delete(f"/api/users/{seeded.operador_id}")
    assert _crear(adm, username="operador").status_code == 201


def test_no_puede_borrarse_a_si_mismo_409(adm, seeded, db):
    _error(adm.delete(f"/api/users/{seeded.admin_id}"), 409, "en_uso")
    assert db.get(User, seeded.admin_id) is not None
    assert adm.get("/api/auth/me").status_code == 200


def test_borrar_inexistente_404(adm):
    _error(adm.delete("/api/users/9999"), 404, "no_encontrado")


# ---- persistencia (REQ-011) ----
def test_los_usuarios_persisten_al_reiniciar_la_app(adm, settings, clock, rate_provider):
    _crear(adm)
    reiniciada = create_app(settings=settings, clock=clock, rate_provider=rate_provider)
    with TestClient(reiniciada, raise_server_exceptions=False) as c:
        assert c.post("/api/auth/login", json={"username": "ana.mora", "password": "Clave#2026-ok"}).status_code == 200
