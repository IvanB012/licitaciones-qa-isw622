"""Reglas puras de licitaciones. El esperado sale de REQ-002, REQ-003 y REQ-004 (CLAUDE.md), no del código."""
from datetime import datetime, timedelta, timezone

import pytest

from app.errors import Conflict, ValidationFailed
from app.rules.constants import STATUS_BORRADOR as B, STATUS_CERRADA as C, STATUS_PUBLICADA as P
from app.rules.tenders import (
    can_transition,
    check_closes_in_future,
    check_transition,
    clean_code,
    clean_description,
    clean_title,
    is_expired,
    parse_budget,
)
from app.rules.timeutil import from_cr, to_iso_utc

NOW = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


# ---- código y título (REQ-002) ----
def test_codigo_se_recorta():  # REQ-002
    assert clean_code("  LIC-2026-001 ") == "LIC-2026-001"


@pytest.mark.parametrize("bad", ["", "   ", "\t\n", None, 123])
def test_codigo_vacio_o_no_texto_se_rechaza(bad):  # REQ-002
    with pytest.raises(ValidationFailed) as exc:
        clean_code(bad)
    assert exc.value.code == "validacion_codigo" and exc.value.status == 422


@pytest.mark.parametrize("bad", ["", "    ", "\t", None, 5])
def test_titulo_vacio_o_no_texto_se_rechaza(bad):  # REQ-002
    with pytest.raises(ValidationFailed) as exc:
        clean_title(bad)
    assert exc.value.code == "validacion_titulo"


def test_titulo_se_recorta():  # REQ-002
    assert clean_title("  Compra de equipo ") == "Compra de equipo"


def test_descripcion_opcional():
    assert clean_description(None) is None
    assert clean_description("   ") is None
    assert clean_description(" texto ") == "texto"
    with pytest.raises(ValidationFailed):
        clean_description(7)


# ---- presupuesto (REQ-002) ----
@pytest.mark.parametrize("text, cents", [("10000000.00", 1_000_000_000), ("0.01", 1), ("1", 100)])
def test_presupuesto_valido(text, cents):  # REQ-002
    assert parse_budget(text) == cents


@pytest.mark.parametrize("bad", ["0", "0.00", "-1", "-0.01", "abc", "1e3", "1,5", "", None, 100, 1.5])
def test_presupuesto_cero_negativo_o_formato_invalido(bad):  # REQ-002
    with pytest.raises(ValidationFailed) as exc:
        parse_budget(bad)
    assert exc.value.code == "monto_invalido"


# ---- cierre futuro (REQ-002) ----
def test_cierre_un_segundo_en_el_futuro_es_valido():  # REQ-002 (límite)
    check_closes_in_future(NOW + timedelta(seconds=1), NOW)


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(seconds=-1), timedelta(days=-30)])
def test_cierre_igual_o_pasado_se_rechaza(delta):  # REQ-002 (límite: exactamente ahora no es futuro)
    with pytest.raises(ValidationFailed) as exc:
        check_closes_in_future(NOW + delta, NOW)
    assert exc.value.code == "cierre_no_futuro"


def test_cierre_sin_zona_horaria_se_rechaza():
    with pytest.raises(ValidationFailed):
        check_closes_in_future(datetime(2026, 12, 1), NOW)


# ---- máquina de estados (REQ-003): las 9 combinaciones ----
VALIDAS = [(B, P), (B, C), (P, C)]
INVALIDAS = [(B, B), (P, B), (P, P), (C, B), (C, P), (C, C)]


@pytest.mark.parametrize("origen, destino", VALIDAS)
def test_transiciones_validas(origen, destino):  # REQ-003
    assert can_transition(origen, destino)
    check_transition(origen, destino)  # no lanza


@pytest.mark.parametrize("origen, destino", INVALIDAS)
def test_transiciones_invalidas(origen, destino):  # REQ-003 (no volver a Borrador, no reabrir Cerrada)
    assert not can_transition(origen, destino)
    with pytest.raises(Conflict) as exc:
        check_transition(origen, destino)
    assert exc.value.code == "transicion_invalida" and exc.value.status == 409


def test_estado_desconocido_no_transiciona():
    assert not can_transition("Abierta", C)


# ---- vencimiento (REQ-004): antes / exactamente / después ----
CIERRE = NOW + timedelta(hours=48)


@pytest.mark.parametrize(
    "ahora, vencida",
    [
        (CIERRE - timedelta(seconds=1), False),
        (CIERRE, True),  # exactamente en el cierre ya vence
        (CIERRE + timedelta(seconds=1), True),
    ],
)
def test_publicada_vence_en_el_instante_de_cierre(ahora, vencida):  # REQ-004
    assert is_expired(P, CIERRE, ahora) is vencida


@pytest.mark.parametrize("estado", [B, C])
def test_solo_publicada_puede_estar_vencida(estado):
    assert is_expired(estado, CIERRE, CIERRE + timedelta(days=1)) is False


# ---- zona horaria ----
def test_from_cr_convierte_a_utc():
    assert from_cr(datetime(2026, 11, 27, 12, 0)) == datetime(2026, 11, 27, 18, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        from_cr(datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc))


def test_to_iso_utc():
    assert to_iso_utc(datetime(2026, 11, 28, 18, 0, tzinfo=timezone.utc)) == "2026-11-28T18:00:00Z"
    with pytest.raises(ValueError):
        to_iso_utc(datetime(2026, 11, 28, 18, 0))
