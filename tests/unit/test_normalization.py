import pytest

from app.rules.normalization import compact_spaces, normalize_code, normalize_name


# REQ-001
@pytest.mark.parametrize(
    "a, b",
    [
        ("Tecnología Norte S.A.", "  tecnología   norte s.a.  "),
        ("Servicios del Valle", "SERVICIOS DEL VALLE"),
        ("Servicios del Valle", "Servicios\tdel Valle"),  # tab y NBSP cuentan como espacio
        ("Tecnología", "Tecnología"),  # NFC vs NFD
    ],
)
def test_normalize_name_equivalentes_dan_misma_clave(a, b):
    assert normalize_name(a) == normalize_name(b)


def test_normalize_name_valor_exacto():
    assert normalize_name("  Tecnología   Norte S.A. ") == "tecnología norte s.a."


def test_normalize_name_nombres_distintos_dan_claves_distintas():
    assert normalize_name("Servicios del Valle") != normalize_name("Servicios del Valle 2")
    assert normalize_name("Norte S.A.") != normalize_name("Norte SA")


def test_normalize_name_vacio_y_solo_espacios():
    assert normalize_name("") == ""
    assert normalize_name("   \t ") == ""


def test_compact_spaces_conserva_mayusculas():
    assert compact_spaces("  Tecnología   Norte  ") == "Tecnología Norte"


# REQ-002
@pytest.mark.parametrize("a, b", [("LIC-2026-001", "lic-2026-001"), ("LIC-2026-001", "  Lic-2026-001 \n")])
def test_normalize_code_equivalentes(a, b):
    assert normalize_code(a) == normalize_code(b)


def test_normalize_code_no_toca_espacios_internos():
    assert normalize_code("LIC 2026") != normalize_code("LIC  2026")
    assert normalize_code("  LIC-1 ") == "lic-1"


def test_normalize_code_distintos():
    assert normalize_code("LIC-2026-001") != normalize_code("LIC-2026-002")


@pytest.mark.parametrize("fn", [normalize_name, normalize_code, compact_spaces])
def test_rechaza_tipos_no_str(fn):
    with pytest.raises(TypeError):
        fn(None)
