"""API de evaluación (contrato §5, §7). Esperado: REQ-007, 008, 009, 010 y 011 de CLAUDE.md, no el código."""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.main import create_app
from app.models import ApprovalRange, ExchangeRate, Offer, Provider, Tender
from app.rules.normalization import normalize_name
from tests.conftest import OPERADOR

CIERRE = "2026-11-28T18:00:00Z"  # el FakeClock arranca el 2026-11-26 12:00Z


@pytest.fixture
def op(client, seeded, login):
    assert login(*OPERADOR).status_code == 200
    return client


@pytest.fixture
def p3(db, clock):
    p = Provider(name="Soluciones Pacífico", name_key=normalize_name("Soluciones Pacífico"), created_at=clock.now())
    db.add(p)
    db.commit()
    return p


def _tender(op, code, budget="1000000.00", publish=True):
    t = op.post("/api/tenders", json={"code": code, "title": f"Licitación {code}", "budget": budget, "closes_at": CIERRE}).json()
    if publish:
        assert op.post(f"/api/tenders/{t['id']}/publish").status_code == 200
    return t


def _offer(op, tender_id, provider_id, amount):
    r = op.post(f"/api/tenders/{tender_id}/offers", json={"provider_id": provider_id, "amount": amount})
    assert r.status_code == 201, r.text
    return r.json()


def _eval(op, tender_id, **params):
    return op.get(f"/api/tenders/{tender_id}/evaluation", params=params)


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


# ---- datos base del enunciado (REQ-007, 008, 009, 010) ----
def test_datos_base_l1(op, seeded):  # P1 9 000 000, P2 9 500 000 sobre 10 000 000
    r = _eval(op, seeded.tender_id)
    assert r.status_code == 200
    assert r.json() == {
        "best_offer": {"offer_id": seeded.offer_p1_id, "provider_id": seeded.p1_id, "amount": "9000000.00"},
        "message": "Mejor oferta: Tecnología Norte S.A.",
        "savings_pct": "10.00",  # REQ-008
        "classification": "Conveniente",
        "approver": "Gerencia",  # REQ-009: 9 000 000 está en [1 000 000; 10 000 000)
        "currency": "CRC",
    }


def test_datos_base_l1_en_usd(op, seeded):  # REQ-010: 9 000 000 / 500 = 18 000,00
    body = _eval(op, seeded.tender_id, currency="USD").json()
    assert body["best_offer"]["amount"] == "18000.00"
    assert (body["currency"], body["rate"], body["rate_date"]) == ("USD", "500.00", "2026-11-26")
    assert (body["savings_pct"], body["classification"], body["approver"]) == ("10.00", "Conveniente", "Gerencia")


def test_la_moneda_no_cambia_el_ahorro_ni_el_aprobador(op, seeded):  # REQ-010: el nivel se decide en CRC
    crc, usd = _eval(op, seeded.tender_id).json(), _eval(op, seeded.tender_id, currency="USD").json()
    assert (crc["savings_pct"], crc["classification"], crc["approver"]) == (
        usd["savings_pct"], usd["classification"], usd["approver"],
    )


def test_alternar_moneda_no_modifica_la_bd(op, seeded, db):  # REQ-010
    def foto():
        db.expire_all()
        return (
            db.scalars(select(Offer.amount_cents).order_by(Offer.id)).all(),
            db.scalars(select(Tender.budget_cents).order_by(Tender.id)).all(),
            db.scalar(select(func.count()).select_from(ExchangeRate)),
        )

    antes = foto()
    _eval(op, seeded.tender_id, currency="USD")
    _eval(op, seeded.tender_id, currency="CRC")
    assert foto() == antes == ([900_000_000, 950_000_000], [1_000_000_000], 1)
    assert _eval(op, seeded.tender_id).json()["best_offer"]["amount"] == "9000000.00"


def test_usd_usa_la_tasa_vigente_y_muestra_su_fecha(op, seeded, db):  # REQ-010
    db.add(
        ExchangeRate(rate_x10000=4_000_000, rate_date=date(2026, 11, 26), source="manual", created_at=datetime(2026, 11, 26, 13, tzinfo=timezone.utc))
    )
    db.commit()
    body = _eval(op, seeded.tender_id, currency="USD").json()
    assert body["best_offer"]["amount"] == "22500.00"  # 9 000 000 / 400
    assert (body["rate"], body["rate_date"]) == ("400.00", "2026-11-26")


def test_usd_sin_tasas_guardadas_usa_el_respaldo_500(op, seeded, db):  # REQ-010 / contrato §5
    db.execute(delete(ExchangeRate))
    db.commit()
    body = _eval(op, seeded.tender_id, currency="USD").json()
    assert (body["best_offer"]["amount"], body["rate"]) == ("18000.00", "500.00")


def test_moneda_en_minusculas_y_por_defecto(op, seeded):
    assert _eval(op, seeded.tender_id, currency="usd").json()["currency"] == "USD"
    assert _eval(op, seeded.tender_id).json()["currency"] == "CRC"
    assert "rate" not in _eval(op, seeded.tender_id).json()  # tasa y fecha solo al ver en USD


@pytest.mark.parametrize("moneda", ["EUR", "", "dolares"])
def test_moneda_invalida_422(op, seeded, moneda):
    _error(_eval(op, seeded.tender_id, currency=moneda), 422, "validacion")


# ---- escenario aislado: presupuesto 1 000 000 con ofertas 900 000 / 950 000 / 1 000 000 (REQ-008, 009) ----
@pytest.mark.parametrize(
    "oferta, ahorro, clase, aprobador",
    [
        ("900000.00", "10.00", "Conveniente", "Encargado de área"),
        ("950000.00", "5.00", "Aceptable", "Encargado de área"),
        ("1000000.00", "0.00", "Válida sin ahorro", "Gerencia"),  # frontera: 1 000 000,00 es Gerencia
    ],
)
def test_clasificacion_en_frontera_con_datos_reseteados(op, seeded, oferta, ahorro, clase, aprobador):  # REQ-008 / 009
    t = _tender(op, "LIC-AISLADA")
    _offer(op, t["id"], seeded.p1_id, oferta)
    body = _eval(op, t["id"]).json()
    assert (body["savings_pct"], body["classification"], body["approver"]) == (ahorro, clase, aprobador)
    assert body["best_offer"]["amount"] == oferta


def test_las_tres_ofertas_del_escenario_aislado_gana_la_menor(op, seeded, p3):  # REQ-007
    t = _tender(op, "LIC-AISLADA")
    _offer(op, t["id"], seeded.p1_id, "1000000.00")
    _offer(op, t["id"], seeded.p2_id, "950000.00")
    menor = _offer(op, t["id"], p3.id, "900000.00")
    body = _eval(op, t["id"]).json()
    assert body["best_offer"]["offer_id"] == menor["id"] and body["savings_pct"] == "10.00"


def test_un_centimo_menos_de_ahorro_ya_no_es_conveniente(op, seeded):  # REQ-008 (límite)
    t = _tender(op, "LIC-AISLADA")
    _offer(op, t["id"], seeded.p1_id, "900000.01")  # ahorro 9,999999 %
    body = _eval(op, t["id"]).json()
    assert body["savings_pct"] == "10.00"  # se muestra redondeado...
    assert body["classification"] == "Aceptable"  # ...pero se clasifica por el valor exacto


# ---- aprobador por rango (REQ-009) ----
@pytest.mark.parametrize(
    "oferta, nivel",
    [
        ("0.01", "Encargado de área"),
        ("999999.99", "Encargado de área"),
        ("1000000.00", "Gerencia"),
        ("9999999.99", "Gerencia"),
        ("10000000.00", "Junta Directiva"),
    ],
)
def test_aprobador_en_las_fronteras_de_los_rangos(op, seeded, oferta, nivel):  # REQ-009
    t = _tender(op, "LIC-GRANDE", budget="20000000.00")
    _offer(op, t["id"], seeded.p1_id, oferta)
    assert _eval(op, t["id"]).json()["approver"] == nivel


def test_el_aprobador_se_decide_sobre_la_mejor_oferta_no_el_presupuesto(op, seeded):  # precisión de alcance
    t = _tender(op, "LIC-GRANDE", budget="20000000.00")  # presupuesto en Junta Directiva
    _offer(op, t["id"], seeded.p1_id, "900000.00")  # pero la oferta es de Encargado de área
    assert _eval(op, t["id"]).json()["approver"] == "Encargado de área"


def test_los_rangos_se_leen_de_la_tabla_configurable(op, seeded, db):  # REQ-009
    assert _eval(op, seeded.tender_id).json()["approver"] == "Gerencia"
    por_nivel = {r.level: r for r in db.scalars(select(ApprovalRange))}
    por_nivel["Encargado de área"].max_cents = 950_000_000
    por_nivel["Gerencia"].min_cents = 950_000_000
    db.commit()
    assert _eval(op, seeded.tender_id).json()["approver"] == "Encargado de área"  # 9 000 000 < 9 500 000


def test_sin_rango_para_el_monto_409(op, seeded, db):  # REQ-009
    db.execute(delete(ApprovalRange).where(ApprovalRange.level == "Gerencia"))  # hueco en la configuración
    db.commit()
    _error(_eval(op, seeded.tender_id), 409, "sin_rango_aprobacion")


def test_sin_ningun_rango_409(op, seeded, db):
    db.execute(delete(ApprovalRange))
    db.commit()
    _error(_eval(op, seeded.tender_id), 409, "sin_rango_aprobacion")


def test_sin_ofertas_no_necesita_rango(op, db):  # no hay monto que aprobar
    t = _tender(op, "LIC-VACIA")
    db.execute(delete(ApprovalRange))
    db.commit()
    assert _eval(op, t["id"]).status_code == 200


# ---- desempate (REQ-007) ----
def test_empate_gana_la_registrada_primero(op, seeded, clock):  # REQ-007
    t = _tender(op, "LIC-EMPATE")
    primera = _offer(op, t["id"], seeded.p2_id, "900000.00")
    clock.advance(seconds=30)
    _offer(op, t["id"], seeded.p1_id, "900000.00")
    assert _eval(op, t["id"]).json()["best_offer"]["offer_id"] == primera["id"]


def test_el_desempate_usa_la_hora_de_registro_no_el_id(op, seeded, db, clock):  # REQ-007
    t = _tender(op, "LIC-EMPATE")
    o1 = _offer(op, t["id"], seeded.p1_id, "900000.00")
    clock.advance(seconds=30)
    o2 = _offer(op, t["id"], seeded.p2_id, "900000.00")
    db.expire_all()
    db.get(Offer, o2["id"]).created_at = clock.now() - timedelta(hours=1)  # o2 (id mayor) se registró antes
    db.commit()
    assert o2["id"] > o1["id"]
    assert _eval(op, t["id"]).json()["best_offer"]["offer_id"] == o2["id"]


def test_editar_el_monto_no_cambia_el_orden_de_registro_en_un_empate(op, seeded, clock):  # REQ-007
    t = _tender(op, "LIC-EMPATE")
    primera = _offer(op, t["id"], seeded.p1_id, "950000.00")
    clock.advance(seconds=30)
    segunda = _offer(op, t["id"], seeded.p2_id, "900000.00")
    assert _eval(op, t["id"]).json()["best_offer"]["offer_id"] == segunda["id"]
    op.put(f"/api/offers/{primera['id']}", json={"amount": "900000.00"})  # ahora empatan; created_at de primera no cambió
    assert _eval(op, t["id"]).json()["best_offer"]["offer_id"] == primera["id"]


# ---- sin ofertas (REQ-007) ----
def test_sin_ofertas_validas(op):  # REQ-007
    t = _tender(op, "LIC-VACIA")
    r = _eval(op, t["id"])
    assert r.status_code == 200
    assert r.json() == {
        "best_offer": None,
        "message": "Sin ofertas válidas",
        "savings_pct": None,
        "classification": None,
        "approver": None,
        "currency": "CRC",
    }


def test_sin_ofertas_en_borrador_y_en_usd(op):  # REQ-007 / REQ-010
    t = _tender(op, "LIC-BORR", publish=False)
    body = _eval(op, t["id"], currency="USD").json()
    assert body["best_offer"] is None and body["message"] == "Sin ofertas válidas"
    assert (body["rate"], body["currency"]) == ("500.00", "USD")


# ---- la evaluación sigue los cambios en las ofertas ----
def test_al_borrar_la_mejor_oferta_gana_la_siguiente(op, seeded):  # REQ-007
    op.delete(f"/api/offers/{seeded.offer_p1_id}")
    body = _eval(op, seeded.tender_id).json()
    assert body["best_offer"]["offer_id"] == seeded.offer_p2_id
    assert (body["savings_pct"], body["classification"]) == ("5.00", "Aceptable")  # 9 500 000 sobre 10 000 000


def test_al_editar_a_una_oferta_menor_cambia_la_mejor(op, seeded):  # REQ-007 / 008
    op.put(f"/api/offers/{seeded.offer_p2_id}", json={"amount": "8000000.00"})
    body = _eval(op, seeded.tender_id).json()
    assert body["best_offer"]["offer_id"] == seeded.offer_p2_id
    assert (body["savings_pct"], body["classification"]) == ("20.00", "Conveniente")


def test_una_licitacion_cerrada_se_puede_evaluar(op, seeded):
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    assert _eval(op, seeded.tender_id).json()["best_offer"]["offer_id"] == seeded.offer_p1_id


def test_la_evaluacion_incluye_ofertas_de_distintas_licitaciones_por_separado(op, seeded):
    t = _tender(op, "LIC-OTRA")
    _offer(op, t["id"], seeded.p2_id, "999000.00")
    assert _eval(op, t["id"]).json()["best_offer"]["amount"] == "999000.00"
    assert _eval(op, seeded.tender_id).json()["best_offer"]["offer_id"] == seeded.offer_p1_id


# ---- errores y acceso (REQ-011) ----
def test_licitacion_inexistente_404(op):
    _error(_eval(op, 9999), 404, "no_encontrado")


def test_sin_sesion_401(client, seeded):
    _error(_eval(client, seeded.tender_id), 401, "no_autenticado")


def test_la_evaluacion_persiste_al_reiniciar_la_app(op, seeded, settings, clock, rate_provider):  # REQ-011
    antes = _eval(op, seeded.tender_id).json()
    reiniciada = create_app(settings=settings, clock=clock, rate_provider=rate_provider)
    with TestClient(reiniciada, raise_server_exceptions=False) as c:
        c.post("/api/auth/login", json={"username": OPERADOR[0], "password": OPERADOR[1]})
        assert _eval(c, seeded.tender_id).json() == antes
