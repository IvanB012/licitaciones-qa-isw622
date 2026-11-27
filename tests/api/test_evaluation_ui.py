"""UI de evaluación en el detalle de la licitación (REQ-007, 008, 009, 010, 012). Mismos resultados que la API."""
import pytest
from sqlalchemy import delete, select

from app.models import ApprovalRange, Offer, Provider
from tests.conftest import OPERADOR

CIERRE = "2026-11-28T18:00:00Z"


@pytest.fixture
def ui(client, seeded):
    r = client.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]}, follow_redirects=False)
    assert r.status_code == 303
    client.get("/")  # consume el mensaje de bienvenida
    return client


def _tender(ui, code="LIC-AISLADA", budget="1000000.00"):
    t = ui.post("/api/tenders", json={"code": code, "title": "Escenario", "budget": budget, "closes_at": CIERRE}).json()
    assert ui.post(f"/api/tenders/{t['id']}/publish").status_code == 200
    return t


def _offer(ui, tender_id, provider_id, amount):
    assert ui.post(f"/api/tenders/{tender_id}/offers", json={"provider_id": provider_id, "amount": amount}).status_code == 201


def _page(ui, tender_id, query=""):
    r = ui.get(f"/tenders/{tender_id}{query}")
    assert r.status_code == 200
    return r.text


def test_detalle_muestra_la_evaluacion_de_los_datos_base(ui, seeded):  # REQ-007, 008, 009
    page = _page(ui, seeded.tender_id)
    assert 'data-testid="evaluation-section"' in page
    assert "Tecnología Norte S.A." in page.split('data-testid="evaluation-best-provider">')[1].split("<")[0]
    assert "₡9 000 000,00" in page.split('data-testid="evaluation-best-amount">')[1].split("<")[0]
    assert "10,00 %" in page and 'data-testid="evaluation-classification">Conveniente<' in page
    assert 'data-testid="evaluation-approver">Gerencia<' in page


def test_la_mejor_oferta_se_marca_en_la_tabla(ui, seeded):  # REQ-007
    page = _page(ui, seeded.tender_id)
    assert f'data-testid="offer-best-{seeded.offer_p1_id}"' in page
    assert f'data-testid="offer-best-{seeded.offer_p2_id}"' not in page


def test_vista_usd_muestra_monto_tasa_y_fecha(ui, seeded):  # REQ-010
    page = _page(ui, seeded.tender_id, "?currency=USD")
    assert "$18 000,00" in page.split('data-testid="evaluation-best-amount">')[1].split("<")[0]
    rate = page.split('data-testid="evaluation-rate">')[1].split("<")[0]
    assert "₡500.00 por USD" in rate and "26/11/2026" in rate
    assert "10,00 %" in page and 'data-testid="evaluation-approver">Gerencia<' in page  # el nivel no cambia con la moneda


def test_vista_crc_no_muestra_la_tasa(ui, seeded):
    assert 'data-testid="evaluation-rate"' not in _page(ui, seeded.tender_id, "?currency=CRC")


@pytest.mark.parametrize(
    "oferta, ahorro, clase, aprobador",
    [
        ("900000.00", "10,00 %", "Conveniente", "Encargado de área"),
        ("950000.00", "5,00 %", "Aceptable", "Encargado de área"),
        ("1000000.00", "0,00 %", "Válida sin ahorro", "Gerencia"),
    ],
)
def test_escenario_aislado_en_la_ui(ui, seeded, oferta, ahorro, clase, aprobador):  # REQ-008, 009
    t = _tender(ui)
    _offer(ui, t["id"], seeded.p1_id, oferta)
    page = _page(ui, t["id"])
    assert ahorro in page.split('data-testid="evaluation-savings">')[1].split("<")[0]
    assert f'data-testid="evaluation-classification">{clase}<' in page
    assert f'data-testid="evaluation-approver">{aprobador}<' in page


def test_sin_ofertas_muestra_sin_ofertas_validas(ui):  # REQ-007
    t = _tender(ui, "LIC-VACIA")
    page = _page(ui, t["id"])
    assert 'data-testid="evaluation-message">Sin ofertas válidas<' in page
    for ausente in ("evaluation-best-provider", "evaluation-savings", "evaluation-classification", "evaluation-approver"):
        assert f'data-testid="{ausente}"' not in page


def test_sin_rango_la_pagina_no_falla_y_avisa(ui, seeded, db):  # REQ-009
    db.execute(delete(ApprovalRange).where(ApprovalRange.level == "Gerencia"))
    db.commit()
    r = ui.get(f"/tenders/{seeded.tender_id}")
    assert r.status_code == 200  # la UI no cae: muestra el resto de la evaluación y el motivo
    assert 'data-testid="evaluation-approver-warning"' in r.text and "No hay un rango de aprobación" in r.text
    assert 'data-testid="evaluation-approver">' not in r.text
    assert "10,00 %" in r.text


def test_la_evaluacion_se_actualiza_al_borrar_la_mejor_oferta(ui, seeded):  # REQ-007
    ui.post(f"/offers/{seeded.offer_p1_id}/delete", follow_redirects=False)
    page = _page(ui, seeded.tender_id)
    assert f'data-testid="offer-best-{seeded.offer_p2_id}"' in page
    assert "5,00 %" in page and 'data-testid="evaluation-classification">Aceptable<' in page


def test_al_borrar_todas_las_ofertas_vuelve_sin_ofertas_validas(ui, seeded):  # REQ-007
    for oid in (seeded.offer_p1_id, seeded.offer_p2_id):
        ui.post(f"/offers/{oid}/delete", follow_redirects=False)
    assert 'data-testid="evaluation-message">Sin ofertas válidas<' in _page(ui, seeded.tender_id)


def test_nombre_de_proveedor_con_html_se_escapa_en_la_evaluacion(ui, seeded, db, clock):  # REQ-012
    malo = Provider(name="<script>alert(1)</script>", name_key="x", created_at=clock.now())
    db.add(malo)
    db.commit()
    t = _tender(ui)
    _offer(ui, t["id"], malo.id, "100000.00")
    page = _page(ui, t["id"])
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_la_vista_de_evaluacion_no_modifica_la_bd(ui, seeded, db):  # REQ-010
    antes = db.scalars(select(Offer.amount_cents).order_by(Offer.id)).all()
    _page(ui, seeded.tender_id, "?currency=USD")
    _page(ui, seeded.tender_id, "?currency=CRC")
    db.expire_all()
    assert db.scalars(select(Offer.amount_cents).order_by(Offer.id)).all() == antes == [900_000_000, 950_000_000]


def test_detalle_sigue_exigiendo_sesion(client, seeded):
    r = client.get(f"/tenders/{seeded.tender_id}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
