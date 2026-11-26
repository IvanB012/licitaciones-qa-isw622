from tests.conftest import ADMIN, OPERADOR


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_login_correcto_admin(client, seeded, login):  # REQ-011
    r = login(*ADMIN)
    assert r.status_code == 200
    assert r.json() == {"username": "admin", "role": "admin"}
    cookie = r.headers["set-cookie"].lower()
    assert "session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "password" not in r.text.lower()


def test_login_username_sin_distinguir_mayusculas(client, seeded, login):
    assert login("  ADMIN ", ADMIN[1]).status_code == 200


def test_login_clave_incorrecta(client, seeded, login):
    r = login("admin", "mala")
    assert r.status_code == 401
    assert r.json()["error"] == "credenciales_invalidas"
    assert set(r.json()) == {"error", "detalle"}


def test_login_usuario_inexistente_mismo_error(client, seeded, login):
    r = login("nadie", "x")
    assert r.status_code == 401 and r.json()["error"] == "credenciales_invalidas"


def test_login_usuario_inactivo(client, seeded, login, db):
    from app.models import User

    db.get(User, seeded.operador_id).active = False
    db.commit()
    assert login(*OPERADOR).status_code == 401


def test_login_body_incompleto_422(client):
    r = client.post("/api/auth/login", json={"username": "admin"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validacion" and "password" in body["detalle"]


def test_login_json_malformado_400(client):
    r = client.post("/api/auth/login", content="{no es json", headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json()["error"] == "solicitud_invalida"


def test_me_sin_sesion_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json() == {"error": "no_autenticado", "detalle": "Debe iniciar sesión."}


def test_me_con_sesion_y_logout(client, seeded, login):
    login(*OPERADOR)
    assert client.get("/api/auth/me").json() == {"username": "operador", "role": "operador"}
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_sesion_invalida_si_usuario_se_desactiva(client, seeded, login, db):
    from app.models import User

    login(*ADMIN)
    db.get(User, seeded.admin_id).active = False
    db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_manipulada_no_autentica(client, seeded):
    client.cookies.set("session", "valor-falso.firmado.mal")
    assert client.get("/api/auth/me").status_code == 401
