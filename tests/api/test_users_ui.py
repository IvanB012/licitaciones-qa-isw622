"""UI de usuarios (solo admin): mismas reglas y mismos mensajes que la API. Nunca muestra contraseñas ni hashes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import User
from tests.conftest import ADMIN, OPERADOR


def _login_ui(client, credenciales):
    r = client.post("/login", data={"username": credenciales[0], "password": credenciales[1]}, follow_redirects=False)
    assert r.status_code == 303
    client.get("/")  # consume el mensaje de bienvenida


@pytest.fixture
def ui(client, seeded):
    _login_ui(client, ADMIN)
    return client


def _puede_entrar(app, usuario, clave) -> bool:
    with TestClient(app, raise_server_exceptions=False) as c:
        return c.post("/api/auth/login", json={"username": usuario, "password": clave}).status_code == 200


def _crear(ui, **over):
    datos = {"username": "ana.mora", "password": "Clave#2026-ok", "role": "operador", **over}
    return ui.post("/users/new", data=datos, follow_redirects=False)


def _total(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(User))


# ---- acceso ----
@pytest.mark.parametrize("ruta", ["/users", "/users/new", "/users/1/edit"])
def test_sin_sesion_redirige_a_login(client, seeded, ruta):
    r = client.get(ruta, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


@pytest.mark.parametrize("metodo, ruta", [("get", "/users"), ("get", "/users/new"), ("post", "/users/new"),
                                          ("get", "/users/1/edit"), ("post", "/users/1/edit"), ("post", "/users/1/delete")])
def test_operador_recibe_403_sin_trazas(client, seeded, metodo, ruta):
    _login_ui(client, OPERADOR)
    r = getattr(client, metodo)(ruta, follow_redirects=False)
    assert r.status_code == 403 and 'data-testid="error-message"' in r.text
    assert "Traceback" not in r.text


def test_operador_no_crea_usuarios_por_ui(client, seeded, db):
    _login_ui(client, OPERADOR)
    _crear(client)
    assert _total(db) == 2


def test_el_menu_muestra_usuarios_solo_al_admin(client, seeded):
    _login_ui(client, ADMIN)
    assert 'data-testid="nav-users"' in client.get("/users").text
    client.post("/logout")
    _login_ui(client, OPERADOR)
    assert 'data-testid="nav-users"' not in client.get("/").text


# ---- listado ----
def test_listado_muestra_los_usuarios_del_seed(ui, seeded):
    page = ui.get("/users").text
    for uid, nombre in ((seeded.admin_id, "admin"), (seeded.operador_id, "operador")):
        assert f'data-testid="user-row-{uid}"' in page and nombre in page
    assert 'data-testid="user-new"' in page and "Activo" in page


def test_el_listado_marca_al_usuario_actual_y_no_ofrece_borrarlo(ui, seeded):
    page = ui.get("/users").text
    assert f'data-testid="user-self-{seeded.admin_id}"' in page
    assert f'data-testid="user-delete-{seeded.admin_id}"' not in page
    assert f'data-testid="user-delete-{seeded.operador_id}"' in page


def test_el_listado_no_muestra_hashes_ni_claves(ui):
    page = ui.get("/users").text
    assert "argon2" not in page and "Admin#2026-test" not in page and "Operador#2026-test" not in page


def test_nombre_de_usuario_con_html_se_escapa(ui, db):  # REQ-012 (dato insertado directo en la BD)
    db.add(User(username="<script>alert(1)</script>", password_hash="x", role="operador"))
    db.commit()
    page = ui.get("/users").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page


# ---- crear ----
def test_formulario_de_alta_tiene_los_campos(ui):
    page = ui.get("/users/new").text
    for testid in ("user-username-input", "user-password-input", "user-role-input", "user-submit"):
        assert f'data-testid="{testid}"' in page
    assert 'type="password"' in page


def test_crear_por_ui(ui, db, app):
    r = _crear(ui)
    assert r.status_code == 303 and r.headers["location"] == "/users"
    assert 'data-testid="flash-success"' in ui.get("/users").text
    assert _total(db) == 3
    assert _puede_entrar(app, "ana.mora", "Clave#2026-ok")


@pytest.mark.parametrize(
    "over, status, fragmento",
    [
        ({"username": "ADMIN"}, 409, "Ya existe un usuario"),
        ({"username": " operador "}, 409, "Ya existe un usuario"),
        ({"username": ""}, 422, "obligatorio"),
        ({"username": "con espacio"}, 422, "de 3 a 50 caracteres"),
        ({"password": "corta"}, 422, "entre 8 y 128"),
        ({"password": ""}, 422, "contraseña es obligatoria"),
        ({"role": "superuser"}, 422, "Rol inválido"),
    ],
)
def test_alta_rechazada_por_ui_no_guarda(ui, db, over, status, fragmento):
    r = _crear(ui, **over)
    assert r.status_code == status and fragmento in r.text and 'data-testid="error-message"' in r.text
    assert _total(db) == 2


def test_los_errores_de_ui_coinciden_con_los_de_la_api(ui):
    api = ui.post("/api/users", json={"username": "ana", "password": "corta", "role": "operador"}).json()["detalle"]
    assert api in _crear(ui, password="corta").text


def test_al_fallar_el_alta_no_se_vuelve_a_mostrar_la_contrasena(ui):
    r = _crear(ui, username="ab", password="Secreta#99-visible")
    assert r.status_code == 422
    assert "Secreta#99-visible" not in r.text
    assert 'value="ab"' in r.text  # el usuario sí se conserva


# ---- editar ----
def test_formulario_de_edicion_no_expone_la_clave_y_bloquea_el_usuario(ui, seeded):
    page = ui.get(f"/users/{seeded.operador_id}/edit").text
    assert page.count('name="username"') == 0  # el nombre se muestra pero no es editable
    assert 'value="operador"' in page and "readonly" in page
    assert "argon2" not in page and "Operador#2026-test" not in page
    assert 'data-testid="user-active-input"' in page and " checked" in page


def test_cambiar_rol_por_ui(ui, seeded, db):
    r = ui.post(f"/users/{seeded.operador_id}/edit", data={"role": "admin", "active": "on", "password": ""}, follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    assert db.get(User, seeded.operador_id).role == "admin"


def test_contrasena_vacia_no_la_cambia(ui, seeded, db, app):
    antes = db.get(User, seeded.operador_id).password_hash
    ui.post(f"/users/{seeded.operador_id}/edit", data={"role": "operador", "active": "on", "password": ""})
    db.expire_all()
    assert db.get(User, seeded.operador_id).password_hash == antes
    assert _puede_entrar(app, *OPERADOR)


def test_cambiar_contrasena_por_ui(ui, seeded, app):
    ui.post(f"/users/{seeded.operador_id}/edit", data={"role": "operador", "active": "on", "password": "Nueva#Clave-2026"})
    assert _puede_entrar(app, OPERADOR[0], "Nueva#Clave-2026")
    assert not _puede_entrar(app, *OPERADOR)


def test_desactivar_por_ui_desmarcando_la_casilla(ui, seeded, db, app):
    ui.post(f"/users/{seeded.operador_id}/edit", data={"role": "operador", "password": ""})  # casilla sin marcar
    db.expire_all()
    assert db.get(User, seeded.operador_id).active is False
    assert not _puede_entrar(app, *OPERADOR)
    assert "Inactivo" in ui.get("/users").text


def test_edicion_con_contrasena_corta_no_cambia_nada(ui, seeded, db):
    r = ui.post(f"/users/{seeded.operador_id}/edit", data={"role": "admin", "active": "on", "password": "corta"}, follow_redirects=False)
    assert r.status_code == 422 and "entre 8 y 128" in r.text
    db.expire_all()
    assert db.get(User, seeded.operador_id).role == "operador"


def test_no_puede_desactivarse_a_si_mismo_por_ui(ui, seeded, db):
    r = ui.post(f"/users/{seeded.admin_id}/edit", data={"role": "admin", "password": ""}, follow_redirects=False)
    assert r.status_code == 409 and "No puede desactivar su propio usuario" in r.text
    db.expire_all()
    assert db.get(User, seeded.admin_id).active is True


def test_no_puede_quitarse_el_rol_admin_por_ui(ui, seeded, db):
    r = ui.post(f"/users/{seeded.admin_id}/edit", data={"role": "operador", "active": "on", "password": ""}, follow_redirects=False)
    assert r.status_code == 409 and "quitarse el rol" in r.text
    db.expire_all()
    assert db.get(User, seeded.admin_id).role == "admin"


def test_editar_inexistente_404(ui):
    r = ui.get("/users/9999/edit")
    assert r.status_code == 404 and 'data-testid="error-message"' in r.text


# ---- borrar ----
def test_borrar_por_ui(ui, seeded, db):
    r = ui.post(f"/users/{seeded.operador_id}/delete", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/users"
    assert 'data-testid="flash-success"' in ui.get("/users").text
    assert _total(db) == 1


def test_borrarse_a_si_mismo_se_rechaza_aunque_se_fuerce_la_peticion(ui, seeded, db):
    ui.post(f"/users/{seeded.admin_id}/delete", follow_redirects=False)
    assert 'data-testid="flash-error"' in ui.get("/users").text
    assert _total(db) == 2
    assert ui.get("/users").status_code == 200  # la sesión sigue viva


def test_borrar_inexistente_muestra_error(ui):
    ui.post("/users/9999/delete", follow_redirects=False)
    assert 'data-testid="flash-error"' in ui.get("/users").text
