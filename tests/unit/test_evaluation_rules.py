"""Reglas puras de evaluación. El esperado sale de REQ-007, 008, 009 y 010 (CLAUDE.md), no del código."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.errors import Conflict, ValidationFailed
from app.rules.approval_ranges import Range
from app.rules.evaluation import (
    CLASS_ACEPTABLE,
    CLASS_CONVENIENTE,
    CLASS_SIN_AHORRO,
    NO_OFFERS_MESSAGE,
    approver_for,
    classify_savings,
    parse_currency,
    pick_best,
    savings_pct,
)
from app.rules.money import crc_to_usd

T0 = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

# Rangos de referencia (contrato §6), en céntimos
RANGOS = [
    Range("Encargado de área", 1, 100_000_000),
    Range("Gerencia", 100_000_000, 1_000_000_000),
    Range("Junta Directiva", 1_000_000_000, None),
]


@dataclass(frozen=True)
class Oferta:
    id: int
    amount_cents: int
    created_at: datetime = T0


# ---- mejor oferta (REQ-007) ----
def test_gana_la_menor_oferta():  # REQ-007 (datos del enunciado: P1 9 000 000 y P2 9 500 000)
    p1, p2 = Oferta(1, 900_000_000, T0), Oferta(2, 950_000_000, T0 + timedelta(seconds=1))
    assert pick_best([p2, p1]) is p1


def test_gana_la_menor_aunque_se_registre_despues():  # REQ-007: el orden de registro solo desempata
    primera, segunda = Oferta(1, 950_000_000, T0), Oferta(2, 900_000_000, T0 + timedelta(minutes=5))
    assert pick_best([primera, segunda]) is segunda


def test_empate_gana_la_registrada_primero():  # REQ-007
    tarde = Oferta(1, 900_000_000, T0 + timedelta(seconds=10))
    temprano = Oferta(2, 900_000_000, T0)  # id mayor pero registrada antes
    assert pick_best([tarde, temprano]) is temprano
    assert pick_best([temprano, tarde]) is temprano


def test_empate_total_de_tiempo_gana_el_menor_id():  # REQ-007 (contrato §7)
    a, b = Oferta(7, 100, T0), Oferta(3, 100, T0)
    assert pick_best([a, b]) is b


def test_una_sola_oferta_es_la_mejor():
    unica = Oferta(1, 5, T0)
    assert pick_best([unica]) is unica


def test_sin_ofertas_no_hay_mejor():  # REQ-007
    assert pick_best([]) is None
    assert NO_OFFERS_MESSAGE == "Sin ofertas válidas"


# ---- ahorro y clasificación (REQ-008) con el escenario aislado: presupuesto CRC 1 000 000,00 ----
PRESUPUESTO = 100_000_000


@pytest.mark.parametrize(
    "oferta, pct, clase",
    [
        (90_000_000, "10.00", CLASS_CONVENIENTE),  # 900 000: frontera exacta del 10 %
        (95_000_000, "5.00", CLASS_ACEPTABLE),  # 950 000
        (100_000_000, "0.00", CLASS_SIN_AHORRO),  # 1 000 000: igual al presupuesto
    ],
)
def test_escenario_aislado_10_5_y_0_por_ciento(oferta, pct, clase):  # REQ-008
    assert savings_pct(PRESUPUESTO, oferta) == Decimal(pct)
    assert classify_savings(PRESUPUESTO, oferta) == clase


def test_datos_base_l1_ahorro_10_conveniente():  # REQ-008: P1 9 000 000 sobre 10 000 000
    assert savings_pct(1_000_000_000, 900_000_000) == Decimal("10.00")
    assert classify_savings(1_000_000_000, 900_000_000) == CLASS_CONVENIENTE


@pytest.mark.parametrize(
    "oferta, clase",
    [
        (90_000_000, CLASS_CONVENIENTE),  # 10,00 %
        (90_000_001, CLASS_ACEPTABLE),  # 9,999999 % : un céntimo menos de ahorro ya no es Conveniente
        (90_100_000, CLASS_ACEPTABLE),  # 9,90 %
        (89_999_999, CLASS_CONVENIENTE),  # 10,000001 %
        (99_999_999, CLASS_ACEPTABLE),  # 0,000001 %: hay ahorro, por mínimo que sea
        (1, CLASS_CONVENIENTE),  # 99,999999 %
    ],
)
def test_clasificacion_en_la_frontera_del_diez_por_ciento(oferta, clase):  # REQ-008 (valores límite)
    assert classify_savings(PRESUPUESTO, oferta) == clase


def test_la_clasificacion_usa_el_valor_exacto_no_el_redondeado():  # REQ-008
    # 9,999999 % se MUESTRA como 10.00 pero se clasifica por el valor exacto: Aceptable
    assert savings_pct(PRESUPUESTO, 90_000_001) == Decimal("10.00")
    assert classify_savings(PRESUPUESTO, 90_000_001) == CLASS_ACEPTABLE
    # 0,004 % se muestra como 0.00 pero hay ahorro: Aceptable, no "Válida sin ahorro"
    assert savings_pct(100_000_000, 99_996_000) == Decimal("0.00")
    assert classify_savings(100_000_000, 99_996_000) == CLASS_ACEPTABLE


def test_ahorro_redondea_half_up_a_dos_decimales():  # REQ-008
    assert savings_pct(1_000_000, 999_995) == Decimal("0.00")  # 0,0005 %
    assert savings_pct(100_000, 99_875) == Decimal("0.13")  # 0,125 % -> half up
    assert savings_pct(300, 100) == Decimal("66.67")


def test_ahorro_no_es_float():
    assert isinstance(savings_pct(PRESUPUESTO, 95_000_000), Decimal)


@pytest.mark.parametrize("presupuesto, oferta", [(100, 101), (100, 0), (100, -1), (0, 0), (-5, 1)])
def test_montos_incoherentes_se_rechazan(presupuesto, oferta):
    with pytest.raises(ValueError):
        savings_pct(presupuesto, oferta)
    with pytest.raises(ValueError):
        classify_savings(presupuesto, oferta)


# ---- aprobador (REQ-009): fronteras de los rangos por defecto ----
@pytest.mark.parametrize(
    "centimos, nivel",
    [
        (1, "Encargado de área"),  # 0,01
        (99_999_999, "Encargado de área"),  # 999 999,99
        (100_000_000, "Gerencia"),  # 1 000 000,00 pertenece a Gerencia (semiabierto)
        (900_000_000, "Gerencia"),  # 9 000 000,00 (dato base)
        (999_999_999, "Gerencia"),  # 9 999 999,99
        (1_000_000_000, "Junta Directiva"),  # 10 000 000,00
        (5_000_000_000_00, "Junta Directiva"),
    ],
)
def test_aprobador_por_rango(centimos, nivel):  # REQ-009
    assert approver_for(centimos, RANGOS) == nivel


def test_aprobador_no_depende_del_orden_de_los_rangos():  # REQ-009
    assert approver_for(900_000_000, list(reversed(RANGOS))) == "Gerencia"


def test_los_rangos_son_configurables():  # REQ-009: el nivel sale de la tabla, no de constantes en el código
    otros = [Range("Encargado de área", 1, 500_000_000), Range("Gerencia", 500_000_000, None)]
    assert approver_for(900_000_000, otros) == "Gerencia"
    assert approver_for(499_999_999, otros) == "Encargado de área"
    assert approver_for(900_000_000, RANGOS) == "Gerencia"


def test_monto_sin_rango_configurado_es_409():  # REQ-009 (huecos permitidos al configurar, no al evaluar)
    con_hueco = [Range("Encargado de área", 1, 100_000_000), Range("Junta Directiva", 1_000_000_000, None)]
    with pytest.raises(Conflict) as exc:
        approver_for(500_000_000, con_hueco)
    assert exc.value.code == "sin_rango_aprobacion" and exc.value.status == 409


def test_sin_ningun_rango_es_409():
    with pytest.raises(Conflict) as exc:
        approver_for(1, [])
    assert exc.value.code == "sin_rango_aprobacion"


# ---- moneda (REQ-010) ----
@pytest.mark.parametrize("valor, esperado", [(None, "CRC"), ("CRC", "CRC"), ("usd", "USD"), (" Usd ", "USD")])
def test_moneda_valida(valor, esperado):
    assert parse_currency(valor) == esperado


@pytest.mark.parametrize("malo", ["EUR", "", "  ", "us", 5, ["USD"]])
def test_moneda_invalida_422(malo):
    with pytest.raises(ValidationFailed) as exc:
        parse_currency(malo)
    assert exc.value.status == 422 and exc.value.code == "validacion"


def test_usd_de_la_oferta_base_es_18000():  # REQ-010: 9 000 000 / 500 = 18 000,00
    assert crc_to_usd(900_000_000, Decimal("500.00")) == Decimal("18000.00")
