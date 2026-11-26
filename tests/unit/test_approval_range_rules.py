"""Reglas puras de rangos de aprobación. El esperado sale de REQ-009 (CLAUDE.md) y del contrato §6."""
import pytest

from app.errors import ValidationFailed
from app.rules.approval_ranges import Range, find_overlap, overlaps, validate_range
from seeds.seed import SEED_RANGES

E, G, J = "Encargado de área", "Gerencia", "Junta Directiva"


# ---- validación ----
def test_rango_valido_con_y_sin_tope():  # CP-### / REQ-009
    assert validate_range(E, "0.01", "999999.99") == Range(E, 1, 99_999_999)
    assert validate_range(J, "10000000.00", None) == Range(J, 1_000_000_000, None)
    assert validate_range(J, "10000000.00", "  ") == Range(J, 1_000_000_000, None)


@pytest.mark.parametrize("min_value", ["0", "0.00", "-1", "-0.01"])
def test_minimo_menor_a_un_centimo_se_rechaza(min_value):  # CP-### / REQ-009
    with pytest.raises(ValidationFailed) as exc:
        validate_range(E, min_value, None)
    assert exc.value.code == "rango_invalido" and exc.value.status == 422


@pytest.mark.parametrize("max_value", ["100.00", "99.99", "0.01", "-5"])
def test_maximo_menor_o_igual_al_minimo_se_rechaza(max_value):  # CP-### / REQ-009
    with pytest.raises(ValidationFailed) as exc:
        validate_range(E, "100.00", max_value)
    assert exc.value.code == "rango_invalido"


@pytest.mark.parametrize("level", ["Presidencia", "", None, "gerencia", 5])
def test_nivel_fuera_de_los_tres_permitidos_se_rechaza(level):  # CP-### / REQ-009
    with pytest.raises(ValidationFailed) as exc:
        validate_range(level, "1.00", "2.00")
    assert exc.value.code == "rango_invalido"


@pytest.mark.parametrize("bad", ["abc", "", None, 5, "1e3", "1.234", "1,5"])
def test_minimo_con_formato_invalido_es_rango_invalido(bad):  # CP-### / REQ-009
    with pytest.raises(ValidationFailed) as exc:
        validate_range(E, bad, None)
    assert exc.value.code == "rango_invalido"


def test_maximo_con_formato_invalido_es_rango_invalido():  # CP-### / REQ-009
    with pytest.raises(ValidationFailed) as exc:
        validate_range(E, "1.00", "xyz")
    assert exc.value.code == "rango_invalido"


# ---- traslapes [min, max) ----
def test_traslape_por_un_centimo_se_detecta():  # CP-### / REQ-009
    a = Range(E, 1, 100_000_000)
    b = Range(G, 99_999_999, 1_000_000_000)  # empieza 1 céntimo antes del fin de a
    assert overlaps(a, b) and overlaps(b, a)


def test_rangos_adyacentes_no_se_traslapan():  # CP-### / REQ-009
    a = Range(E, 1, 100_000_000)
    b = Range(G, 100_000_000, 1_000_000_000)
    assert not overlaps(a, b) and not overlaps(b, a)


def test_huecos_se_permiten():  # CP-### / REQ-009
    assert not overlaps(Range(E, 1, 100), Range(G, 200, 300))


def test_maximo_nulo_es_infinito():  # CP-### / REQ-009
    sin_tope = Range(J, 1_000_000_000, None)
    assert overlaps(sin_tope, Range(G, 5_000_000_000, 6_000_000_000))  # otro por encima: choca
    assert overlaps(sin_tope, Range(G, 999_999_999, 1_000_000_001))
    assert not overlaps(sin_tope, Range(G, 100, 1_000_000_000))  # termina justo donde empieza
    assert overlaps(sin_tope, Range(E, 1, None))  # dos sin tope siempre chocan


def test_un_rango_contenido_en_otro_se_traslapa():  # CP-### / REQ-009
    assert overlaps(Range(E, 1, 1000), Range(G, 10, 20))


def test_find_overlap_devuelve_el_primero_que_choca_o_none():  # CP-### / REQ-009
    otros = [Range(E, 1, 100), Range(G, 100, 200)]
    assert find_overlap(Range(J, 150, None), otros) == otros[1]
    assert find_overlap(Range(J, 200, None), otros) is None


def test_rangos_del_seed_son_validos_y_no_se_traslapan():  # CP-### / REQ-009
    rangos = [validate_range(lv, f"{lo // 100}.{lo % 100:02d}", None if hi is None else f"{hi // 100}.{hi % 100:02d}")
              for lv, lo, hi in SEED_RANGES]
    assert len(rangos) == 3
    for i, a in enumerate(rangos):
        for b in rangos[i + 1:]:
            assert not overlaps(a, b), (a, b)
