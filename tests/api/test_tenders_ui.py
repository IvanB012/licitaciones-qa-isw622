"""UI de licitaciones: mismas reglas y mismos mensajes que la API (REQ-002, 003, 010, 011, 012)."""
import re

import pytest
from sqlalchemy import select

from app.models import Tender
from tests.conftest import OPERADOR

FORM = {
    "code": "LIC-2026-060",
    "title": "Compra de papelería",
    "description": "",
    "budget": "500000.00",
    "closes_at": "2026-11-28T10:00",  # hora de Costa Rica = 16:00 UTC
}


@pytest.fixture
def ui(client, seeded):
    r = client.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]}, follow_redirects=False)
    assert r.status_code == 303
    return client


def _new(ui, **over):
    return ui.post("/tenders/new", data={**FORM, **over}, follow_redirects=False)


def _id_from_redirect(r) -> int:
    return int(re.fullmatch(r"/tenders/(\d+)", r.headers["location"]).group(1))


def test_rutas_exigen_sesion(client, seeded):
    for path in ("/tenders", "/tenders/new", f"/tenders/{seeded.tender_id}"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.post("/tenders/new", data=FORM, follow_redirects=False).headers["location"] == "/login"


def test_listado_muestra_seed_con_testids(ui, seeded):
    page = ui.get("/tenders")
    assert page.status_code == 200
    assert f'data-testid="tender-row-{seeded.tender_id}"' in page.text and "LIC-2026-001" in page.text
    assert 'data-testid="tender-new"' in page.text and "₡10 000 000,00" in page.text
    assert 'data-testid="status-badge"' in page.text


def test_crear_por_ui_redirige_al_detalle_en_borrador(ui, db):  # REQ-002
    r = _new(ui)
    assert r.status_code == 303
    tender = db.get(Tender, _id_from_redirect(r))
    assert tender.status == "Borrador" and tender.budget_cents == 50_000_000
    assert tender.closes_at.hour == 16  # 10:00 hora CR (UTC−6) -> 16:00 UTC
    page = ui.get(r.headers["location"])
    assert 'data-testid="flash-success"' in page.text and "LIC-2026-060" in page.text


def test_crear_con_error_muestra_el_mismo_detalle_que_la_api(ui):  # REQ-011
    api = ui.post("/api/tenders", json={"code": "x", "title": "x", "budget": "0", "closes_at": "2026-11-28T18:00:00Z"})
    r = _new(ui, budget="0")
    assert r.status_code == 422
    assert 'data-testid="error-message"' in r.text
    assert api.json()["detalle"] in r.text
    assert 'value="LIC-2026-060"' in r.text  # conserva lo escrito


@pytest.mark.parametrize(
    "over, status, fragmento",
    [
        ({"title": "   "}, 422, "título"),
        ({"code": "lic-2026-001 "}, 409, "Ya existe"),
        ({"closes_at": "2026-11-26T06:00"}, 422, "futuras"),  # 06:00 CR == 12:00 UTC == ahora
        ({"closes_at": "no-es-fecha"}, 422, "no son válidas"),
        ({"budget": "-3"}, 422, "mayor que cero"),
    ],
)
def test_crear_rechazos_por_ui(ui, over, status, fragmento):  # REQ-002
    r = _new(ui, **over)
    assert r.status_code == status and fragmento in r.text


def test_titulo_con_script_se_escapa(ui):  # REQ-012
    r = _new(ui, title="<script>alert(1)</script>")
    page = ui.get(r.headers["location"])
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page.text
    assert "&lt;script&gt;" in ui.get("/tenders").text


def test_publicar_cerrar_y_no_reabrir_por_ui(ui, db):  # REQ-003
    tid = _id_from_redirect(_new(ui))
    detalle = ui.get(f"/tenders/{tid}").text
    assert 'data-testid="tender-publish"' in detalle and 'data-testid="tender-delete"' in detalle

    r = ui.post(f"/tenders/{tid}/publish", follow_redirects=False)
    assert r.status_code == 303
    detalle = ui.get(f"/tenders/{tid}").text
    assert "Publicada" in detalle and 'data-testid="tender-publish"' not in detalle
    assert 'data-testid="tender-edit"' not in detalle  # solo se edita en Borrador

    ui.post(f"/tenders/{tid}/close")
    detalle = ui.get(f"/tenders/{tid}").text
    assert "Cerrada" in detalle and 'data-testid="tender-close"' not in detalle

    ui.post(f"/tenders/{tid}/publish", follow_redirects=False)  # intento de reabrir
    page = ui.get(f"/tenders/{tid}")
    assert 'data-testid="flash-error"' in page.text and "No se puede pasar" in page.text
    db.expire_all()
    assert db.get(Tender, tid).status == "Cerrada"


def test_editar_por_ui_solo_en_borrador(ui, seeded, db):  # contrato §5
    tid = _id_from_redirect(_new(ui))
    page = ui.get(f"/tenders/{tid}/edit")
    assert page.status_code == 200 and 'value="2026-11-28T10:00"' in page.text and 'value="500000.00"' in page.text

    r = ui.post(f"/tenders/{tid}/edit", data={**FORM, "title": "Otro título"}, follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    assert db.get(Tender, tid).title == "Otro título"

    r = ui.get(f"/tenders/{seeded.tender_id}/edit", follow_redirects=False)  # Publicada
    assert r.status_code == 303 and r.headers["location"] == f"/tenders/{seeded.tender_id}"


def test_eliminar_por_ui(ui, seeded, db):
    tid = _id_from_redirect(_new(ui))
    r = ui.post(f"/tenders/{tid}/delete", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/tenders"
    db.expire_all()
    assert db.get(Tender, tid) is None
    ui.post(f"/tenders/{seeded.tender_id}/delete", follow_redirects=False)  # Publicada con ofertas: rechazada
    assert 'data-testid="flash-error"' in ui.get(f"/tenders/{seeded.tender_id}").text


def test_detalle_inexistente_404(ui):
    r = ui.get("/tenders/9999")
    assert r.status_code == 404 and 'data-testid="error-message"' in r.text


def test_filtro_por_estado(ui, seeded):
    nueva = _id_from_redirect(_new(ui))
    publicadas = ui.get("/tenders", params={"status": "Publicada"}).text
    assert f'data-testid="tender-row-{seeded.tender_id}"' in publicadas
    assert f'data-testid="tender-row-{nueva}"' not in publicadas
    borradores = ui.get("/tenders", params={"status": "Borrador"}).text
    assert f'data-testid="tender-row-{nueva}"' in borradores
    assert f'data-testid="tender-row-{seeded.tender_id}"' not in borradores


def test_vista_usd_no_modifica_la_bd(ui, seeded, db):  # REQ-010
    antes = db.scalar(select(Tender.budget_cents).where(Tender.id == seeded.tender_id))
    usd = ui.get("/tenders?currency=USD").text
    assert "$20 000,00" in usd  # 10 000 000 / 500
    assert 'data-testid="rate-info"' in usd and "₡500.00 por USD" in usd
    detalle = ui.get(f"/tenders/{seeded.tender_id}").text  # la vista elegida se recuerda
    assert "$20 000,00" in detalle
    assert "₡10 000 000,00" in ui.get("/tenders?currency=CRC").text
    db.expire_all()
    assert db.scalar(select(Tender.budget_cents).where(Tender.id == seeded.tender_id)) == antes == 1_000_000_000


def test_publicada_vencida_se_marca_y_sigue_publicada(ui, seeded, clock, db):  # REQ-004 (vista)
    from datetime import timedelta

    assert 'data-testid="expired-badge"' not in ui.get("/tenders").text
    clock.advance(timedelta(hours=48))  # exactamente el cierre
    assert 'data-testid="expired-badge"' in ui.get("/tenders").text
    db.expire_all()
    assert db.get(Tender, seeded.tender_id).status == "Publicada"
