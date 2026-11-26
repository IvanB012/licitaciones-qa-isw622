"""Reglas puras de ofertas. El esperado sale de REQ-004 y REQ-005 (CLAUDE.md), no del código."""
from datetime import datetime, timedelta, timezone

import pytest

from app.errors import Conflict, ValidationFailed
from app.rules.constants import STATUS_BORRADOR, STATUS_CERRADA, STATUS_PUBLICADA
from app.rules.offers import check_tender_open, parse_amount

CIERRE = datetime(2026, 11, 28, 12, 0, 0, tzinfo=timezone.utc)
PRESUPUESTO = 100_000_000  # CRC 1 000 000,00 (escenario aislado del enunciado)


# ---- vencimiento (REQ-004): antes / exactamente / después ----
@pytest.mark.parametrize("delta", [timedelta(hours=-48), timedelta(minutes=-1), timedelta(seconds=-1)])
def test_antes_del_cierre_se_acepta(delta):  # REQ-004
    check_tender_open(STATUS_PUBLICADA, CIERRE, CIERRE + delta)


def test_exactamente_en_el_cierre_se_rechaza():  # REQ-004 (límite clave)
    with pytest.raises(Conflict) as exc:
        check_tender_open(STATUS_PUBLICADA, CIERRE, CIERRE)
    assert exc.value.code == "licitacion_vencida" and exc.value.status == 409


@pytest.mark.parametrize("delta", [timedelta(seconds=1), timedelta(hours=1), timedelta(days=30)])
def test_despues_del_cierre_se_rechaza(delta):  # REQ-004
    with pytest.raises(Conflict) as exc:
        check_tender_open(STATUS_PUBLICADA, CIERRE, CIERRE + delta)
    assert exc.value.code == "licitacion_vencida"


@pytest.mark.parametrize("estado", [STATUS_BORRADOR, STATUS_CERRADA])
def test_solo_se_ofertan_licitaciones_publicadas(estado):  # REQ-004
    with pytest.raises(Conflict) as exc:
        check_tender_open(estado, CIERRE, CIERRE - timedelta(hours=1))  # aunque el plazo no haya vencido
    assert exc.value.code == "licitacion_no_publicada" and exc.value.status == 409


def test_el_estado_se_revisa_antes_que_el_vencimiento():
    with pytest.raises(Conflict) as exc:
        check_tender_open(STATUS_CERRADA, CIERRE, CIERRE + timedelta(days=1))
    assert exc.value.code == "licitacion_no_publicada"


# ---- montos (REQ-005) con el presupuesto CRC 1 000 000,00 ----
@pytest.mark.parametrize(
    "texto, centimos",
    [
        ("900000.00", 90_000_000),
        ("950000.00", 95_000_000),
        ("1000000.00", 100_000_000),  # igual al presupuesto: VÁLIDA
        ("999999.99", 99_999_999),
        ("0.01", 1),  # mínimo positivo
        ("  500000  ", 50_000_000),
    ],
)
def test_montos_validos(texto, centimos):  # REQ-005
    assert parse_amount(texto, PRESUPUESTO) == centimos


@pytest.mark.parametrize("texto", ["1000000.01", "1000001", "5000000.00", "99999999.99"])
def test_monto_sobre_el_presupuesto_se_rechaza(texto):  # REQ-005 (un céntimo por encima ya se rechaza)
    with pytest.raises(ValidationFailed) as exc:
        parse_amount(texto, PRESUPUESTO)
    assert exc.value.code == "monto_excede_presupuesto" and exc.value.status == 422


@pytest.mark.parametrize("texto", ["0", "0.00", "-1", "-0.01", "-1000000.00"])
def test_monto_cero_o_negativo_se_rechaza(texto):  # REQ-005
    with pytest.raises(ValidationFailed) as exc:
        parse_amount(texto, PRESUPUESTO)
    assert exc.value.code == "monto_invalido"


@pytest.mark.parametrize("malo", ["abc", "", "1e3", "1,5", "1000.001", None, 900000, 900000.5, True])
def test_monto_con_formato_invalido_se_rechaza(malo):  # REQ-005 / REQ-011
    with pytest.raises(ValidationFailed) as exc:
        parse_amount(malo, PRESUPUESTO)
    assert exc.value.code == "monto_invalido"


def test_el_limite_depende_del_presupuesto_de_cada_licitacion():  # REQ-005
    assert parse_amount("9500000.00", 1_000_000_000) == 950_000_000  # L1 del seed (presupuesto 10 000 000)
    with pytest.raises(ValidationFailed):
        parse_amount("9500000.00", PRESUPUESTO)
