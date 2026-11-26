from tests.conftest import ADMIN, OPERADOR


def _ui_login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)


def test_ui_sin_sesion_redirige_a_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_ui_ruta_desconocida_sin_sesion_redirige_a_login(client):
    r = client.get("/providers", follow_redirects=False)  # aún no implementada
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_login_page_publica_con_bootstrap_local(client):
    r = client.get("/login")
    assert r.status_code == 200
    for testid in ("login-username-input", "login-password-input", "login-submit"):
        assert f'data-testid="{testid}"' in r.text
    assert "cdn" not in r.text.lower() and "/static/vendor/bootstrap/css/bootstrap.min.css" in r.text
    assert client.get("/static/vendor/bootstrap/css/bootstrap.min.css").status_code == 200
    assert client.get("/static/vendor/bootstrap/js/bootstrap.bundle.min.js").status_code == 200


def test_login_ui_correcto_y_panel(client, seeded):
    r = _ui_login(client, *ADMIN)
    assert r.status_code == 303 and r.headers["location"] == "/"
    page = client.get("/")
    assert page.status_code == 200
    assert 'data-testid="flash-success"' in page.text
    assert 'data-testid="welcome-message"' in page.text and "admin" in page.text
    assert 'data-testid="currency-toggle"' in page.text and 'data-testid="logout-button"' in page.text
    assert 'data-testid="nav-users"' in page.text  # admin ve Usuarios
    assert 'data-testid="tender-row-%d"' % seeded.tender_id in page.text and "LIC-2026-001" in page.text


def test_navbar_operador_no_ve_secciones_admin(client, seeded):
    _ui_login(client, *OPERADOR)
    page = client.get("/")
    assert 'data-testid="nav-providers"' in page.text
    assert 'data-testid="nav-users"' not in page.text and 'data-testid="nav-approval-ranges"' not in page.text


def test_login_ui_incorrecto_muestra_error(client, seeded):
    r = _ui_login(client, "admin", "mala")
    assert r.status_code == 401
    assert 'data-testid="error-message"' in r.text and "incorrectos" in r.text


def test_login_ui_escapa_html(client, seeded):  # REQ-012
    payload = '"><script>alert(1)</script>'
    r = _ui_login(client, payload, "x")
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text


def test_logout_ui(client, seeded):
    _ui_login(client, *ADMIN)
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/", follow_redirects=False).status_code == 303


def test_login_page_con_sesion_redirige_al_panel(client, seeded):
    _ui_login(client, *ADMIN)
    assert client.get("/login", follow_redirects=False).headers["location"] == "/"


def test_alternar_moneda_solo_cambia_la_vista(client, seeded, db):  # REQ-010
    from sqlalchemy import select

    from app.models import Tender

    _ui_login(client, *ADMIN)
    antes = db.scalar(select(Tender.budget_cents))
    page = client.get("/?currency=USD")
    assert 'data-testid="currency-usd"' in page.text and "btn btn-outline-light active" in page.text
    assert client.get("/").text.count(" active\"") >= 1  # se recuerda la última moneda elegida
    db.expire_all()
    assert db.scalar(select(Tender.budget_cents)) == antes
