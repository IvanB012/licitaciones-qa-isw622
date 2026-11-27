"""UI de rangos de aprobación (solo admin): mismas reglas y mensajes que la API (REQ-009, REQ-011)."""
import pytest

from app.models import ApprovalRange
from tests.conftest import ADMIN, OPERADOR

E, G, J = "Encargado de área", "Gerencia", "Junta Directiva"


def _ui_login(client, creds):
    r = client.post("/login", data={"username": creds[0], "password": creds[1]}, follow_redirects=False)
    assert r.status_code == 303
    return client


@pytest.fixture
def adm(client, seeded):
    return _ui_login(client, ADMIN)


@pytest.fixture
def vacio(adm, db):
    db.query(ApprovalRange).delete()
    db.commit()
    return adm


def _new(c, level, lo, hi=""):
    return c.post("/approval-ranges/new", data={"level": level, "min": lo, "max": hi}, follow_redirects=False)


def test_sin_sesion_redirige_a_login(client, seeded):  # REQ-011
    for path in ("/approval-ranges", "/approval-ranges/new", "/approval-ranges/1/edit"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"


def test_operador_recibe_403_por_url_y_no_ve_el_enlace(client, seeded):  # REQ-011
    _ui_login(client, OPERADOR)
    inicio = client.get("/").text
    assert 'data-testid="nav-approval-ranges"' not in inicio
    for path in ("/approval-ranges", "/approval-ranges/new", "/approval-ranges/1/edit"):
        assert client.get(path).status_code == 403
    assert client.post("/approval-ranges/new", data={"level": E, "min": "1.00"}).status_code == 403
    assert client.post("/approval-ranges/1/delete").status_code == 403


def test_admin_ve_el_enlace_y_el_listado_con_testids(adm, db):  # REQ-009
    assert 'data-testid="nav-approval-ranges"' in adm.get("/").text
    page = adm.get("/approval-ranges")
    assert page.status_code == 200
    for r in db.query(ApprovalRange):
        assert f'data-testid="approval-range-row-{r.id}"' in page.text
    assert "₡1 000 000,00" in page.text and "Sin tope" in page.text and 'data-testid="approval-range-new"' in page.text


def test_formulario_tiene_testids(adm):  # REQ-013
    page = adm.get("/approval-ranges/new").text
    for testid in ("approval-range-level-input", "approval-range-min-input", "approval-range-max-input", "approval-range-submit"):
        assert f'data-testid="{testid}"' in page


def test_alta_correcta(vacio, db):  # REQ-009
    r = _new(vacio, G, "1000000.00", "10000000.00")
    assert r.status_code == 303 and r.headers["location"] == "/approval-ranges"
    assert 'data-testid="flash-success"' in vacio.get("/approval-ranges").text
    row = db.query(ApprovalRange).one()
    assert (row.level, row.min_cents, row.max_cents) == (G, 100_000_000, 1_000_000_000)


def test_alta_sin_maximo_es_sin_tope(vacio, db):  # REQ-009
    _new(vacio, J, "10000000.00", "")
    assert db.query(ApprovalRange).one().max_cents is None


@pytest.mark.parametrize(
    "level, lo, hi, fragmento",
    [(E, "0", "", "al menos 0.01"), (E, "10.00", "10.00", "mayor que el mínimo"),
     ("", "1.00", "", "Nivel inválido"), (E, "abc", "", "mínimo")],
)
def test_errores_422_se_muestran_en_error_message(adm, level, lo, hi, fragmento):  # REQ-009
    r = _new(adm, level, lo, hi)
    assert r.status_code == 422
    assert 'data-testid="error-message"' in r.text and fragmento in r.text


def test_traslape_por_un_centimo_por_ui(vacio):  # REQ-009
    _new(vacio, E, "0.01", "1000000.00")
    r = _new(vacio, G, "999999.99", "10000000.00")
    assert r.status_code == 409 and "se traslapa" in r.text and 'data-testid="error-message"' in r.text


def test_nivel_duplicado_por_ui(adm):  # REQ-009
    r = _new(adm, E, "50000000.00", "60000000.00")
    assert r.status_code == 409 and "Ya existe un rango" in r.text


def test_error_ui_usa_el_mismo_detalle_que_la_api(adm):  # REQ-011
    api = adm.post("/api/approval-ranges", json={"level": E, "min": "0", "max": None})
    assert api.json()["detalle"] in _new(adm, E, "0").text


def test_editar_sin_chocar_consigo_mismo_por_ui(adm, db):  # REQ-009
    g = db.query(ApprovalRange).filter_by(level=G).one()
    r = adm.post(f"/approval-ranges/{g.id}/edit", data={"level": G, "min": "1000000.00", "max": "9999999.99"}, follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    assert db.get(ApprovalRange, g.id).max_cents == 999_999_999


def test_editar_con_traslape_muestra_error(adm, db):  # REQ-009
    g = db.query(ApprovalRange).filter_by(level=G).one()
    r = adm.post(f"/approval-ranges/{g.id}/edit", data={"level": G, "min": "999999.99", "max": "10000000.00"})
    assert r.status_code == 409 and "se traslapa" in r.text


def test_editar_inexistente_404(adm):  # REQ-011
    assert adm.get("/approval-ranges/99999/edit").status_code == 404


def test_borrar_por_ui(adm, db):  # REQ-009
    gid = db.query(ApprovalRange).filter_by(level=G).one().id
    assert adm.post(f"/approval-ranges/{gid}/delete", follow_redirects=False).status_code == 303
    assert 'data-testid="flash-success"' in adm.get("/approval-ranges").text
    db.expire_all()
    assert db.get(ApprovalRange, gid) is None
