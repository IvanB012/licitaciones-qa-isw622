"""UI de proveedores: mismas reglas y mismos mensajes que la API (REQ-001, 011, 012)."""
import pytest

from app.models import Provider
from tests.conftest import OPERADOR


@pytest.fixture
def ui(client, seeded):
    r = client.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]}, follow_redirects=False)
    assert r.status_code == 303
    return client


def _new(ui, name="Insumos del Sur", contact_email=""):
    return ui.post("/providers/new", data={"name": name, "contact_email": contact_email}, follow_redirects=False)


def test_rutas_exigen_sesion(client, seeded):  # REQ-011
    for path in ("/providers", "/providers/new", f"/providers/{seeded.p1_id}/edit"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.post("/providers/new", data={"name": "X"}, follow_redirects=False).headers["location"] == "/login"


def test_listado_muestra_seed_con_testids(ui, seeded):  # REQ-001
    page = ui.get("/providers")
    assert page.status_code == 200
    assert f'data-testid="provider-row-{seeded.p1_id}"' in page.text and "Tecnología Norte S.A." in page.text
    assert 'data-testid="provider-new"' in page.text
    assert f'data-testid="provider-edit-{seeded.p2_id}"' in page.text


def test_formulario_tiene_testids(ui):  # REQ-013
    page = ui.get("/providers/new").text
    for testid in ("provider-name-input", "provider-email-input", "provider-submit", "provider-form"):
        assert f'data-testid="{testid}"' in page


def test_alta_correcta_redirige_al_listado_con_mensaje(ui, db):  # REQ-001
    r = _new(ui, "  Insumos   del Sur ", "ventas@sur.cr")
    assert r.status_code == 303 and r.headers["location"] == "/providers"
    page = ui.get("/providers")
    assert 'data-testid="flash-success"' in page.text and "Insumos del Sur" in page.text
    prov = db.query(Provider).filter_by(name="Insumos del Sur").one()
    assert prov.contact_email == "ventas@sur.cr"


@pytest.mark.parametrize(
    "name, status, fragmento",
    [
        ("Acme & Co", 422, "solo admite letras"),
        ("<script>alert(1)</script>", 422, "solo admite letras"),
        ("   ", 422, "obligatorio"),
        ("  tecnología   NORTE s.a. ", 409, "Ya existe"),
    ],
)
def test_alta_con_error_se_muestra_en_error_message(ui, name, status, fragmento):  # CP-015 / REQ-012
    r = _new(ui, name)
    assert r.status_code == status
    assert 'data-testid="error-message"' in r.text and fragmento in r.text


def test_error_ui_usa_el_mismo_detalle_que_la_api(ui):  # REQ-011
    api = ui.post("/api/providers", json={"name": "Acme & Co"})
    r = _new(ui, "Acme & Co")
    assert api.json()["detalle"] in r.text


def test_valores_renderizados_quedan_escapados(ui):  # CP-015 / REQ-012
    r = _new(ui, "<script>alert(1)</script>", 'x"><script>alert(2)</script>')
    assert "<script>alert(1)</script>" not in r.text and "<script>alert(2)</script>" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text  # el valor escrito se conserva, escapado


def test_nombre_guardado_se_escapa_en_listado_y_edicion(ui, db, clock):  # CP-015 / REQ-012
    # Aunque un dato malicioso llegara a la BD, las plantillas lo escapan (autoescape).
    db.add(Provider(name="<img src=x onerror=alert(1)>", name_key="evil", contact_email="<b>x</b>", created_at=clock.now()))
    db.commit()
    pid = db.query(Provider).filter_by(name_key="evil").one().id
    listado, edicion = ui.get("/providers").text, ui.get(f"/providers/{pid}/edit").text
    for page in (listado, edicion):
        assert "<img src=x" not in page and "<b>x</b>" not in page
        assert "&lt;img src=x" in page
    assert 'data-testid="provider-row-' in listado


def test_editar_por_ui_sin_falso_duplicado(ui, seeded, db):  # REQ-001
    r = ui.post(f"/providers/{seeded.p1_id}/edit", data={"name": "TECNOLOGÍA NORTE S.A.", "contact_email": ""},
                follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    assert db.get(Provider, seeded.p1_id).name == "TECNOLOGÍA NORTE S.A."


def test_editar_a_nombre_de_otro_muestra_error(ui, seeded):  # REQ-001
    r = ui.post(f"/providers/{seeded.p1_id}/edit", data={"name": "Servicios del Valle", "contact_email": ""})
    assert r.status_code == 409 and 'data-testid="error-message"' in r.text and "Ya existe" in r.text


def test_editar_inexistente_404(ui):  # REQ-011
    assert ui.get("/providers/99999/edit").status_code == 404


def test_borrar_sin_ofertas_por_ui(ui, db):  # REQ-001
    _new(ui)
    pid = db.query(Provider).filter_by(name="Insumos del Sur").one().id
    r = ui.post(f"/providers/{pid}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert 'data-testid="flash-success"' in ui.get("/providers").text
    db.expire_all()
    assert db.get(Provider, pid) is None


def test_borrar_con_ofertas_muestra_error_y_conserva(ui, seeded, db):  # REQ-001
    api = ui.delete(f"/api/providers/{seeded.p1_id}")
    ui.post(f"/providers/{seeded.p1_id}/delete", follow_redirects=False)
    page = ui.get("/providers")
    assert 'data-testid="flash-error"' in page.text and api.json()["detalle"] in page.text
    db.expire_all()
    assert db.get(Provider, seeded.p1_id) is not None
