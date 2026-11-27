"""Reglas puras de proveedores. El esperado sale de REQ-001 y REQ-012 (CLAUDE.md), no del código."""
import unicodedata

import pytest

from app.errors import ValidationFailed
from app.rules.normalization import normalize_name
from app.rules.providers import clean_email, clean_name


# ---- nombres válidos (REQ-012) ----
@pytest.mark.parametrize(
    "name",
    ["Tecnología Norte S.A.", "Servicios del Valle", "Ñandú (CR), S.A.", "Proveedor 24 Horas", "A"],
)
def test_nombre_valido_se_acepta(name):  # REQ-012
    assert clean_name(name) == name


def test_nombre_se_recorta_y_compacta_espacios():  # REQ-001
    assert clean_name("  Tecnología   Norte   S.A. ") == "Tecnología Norte S.A."


# ---- nombres inválidos (REQ-012) ----
@pytest.mark.parametrize(
    "bad",
    [
        "<script>alert(1)</script>",
        "Acme & Co",
        "Nombre; DROP TABLE",
        "Acme\tCo",
        "Acme\nCo",
        "Acme_Co",
        "Acme-Co",
        "Acme 😀",
        "O'Brien",
        "a@b",
    ],
)
def test_nombre_con_caracteres_no_permitidos_se_rechaza(bad):  # CP-015 / REQ-012
    with pytest.raises(ValidationFailed) as exc:
        clean_name(bad)
    assert exc.value.code == "validacion_nombre" and exc.value.status == 422


@pytest.mark.parametrize("bad", ["", "   ", "\t \n", None, 123])
def test_nombre_vacio_o_no_texto_se_rechaza(bad):  # REQ-001
    with pytest.raises(ValidationFailed) as exc:
        clean_name(bad)
    assert exc.value.code == "validacion_nombre"


# ---- equivalencia para duplicados (REQ-001) ----
def test_nombres_equivalentes_tienen_la_misma_clave():  # CP-001 / REQ-001
    assert normalize_name(clean_name("  tecnología   NORTE s.a. ")) == normalize_name(
        clean_name("Tecnología Norte S.A.")
    )


def test_tilde_compuesta_y_descompuesta_son_el_mismo_nombre():  # REQ-001
    compuesto = "Tecnología Norte"  # í precompuesta
    descompuesto = unicodedata.normalize("NFD", compuesto)  # i + acento combinante
    assert compuesto != descompuesto
    assert clean_name(descompuesto) == compuesto  # el descompuesto NO se rechaza: se normaliza
    assert normalize_name(clean_name(descompuesto)) == normalize_name(clean_name(compuesto))


def test_nombres_distintos_tienen_claves_distintas():  # REQ-001
    assert normalize_name("Servicios del Valle") != normalize_name("Servicios del Valle 2")


# ---- correo opcional ----
@pytest.mark.parametrize("empty", [None, "", "   "])
def test_correo_opcional_vacio_es_none(empty):  # REQ-001
    assert clean_email(empty) is None


def test_correo_valido_se_recorta():  # REQ-001
    assert clean_email("  ventas@norte.co.cr ") == "ventas@norte.co.cr"


@pytest.mark.parametrize("bad", ["sin-arroba", "a@b", "a b@c.com", "<x>@c.com", "a@c.com;b@d.com", 5])
def test_correo_invalido_se_rechaza(bad):  # REQ-001
    with pytest.raises(ValidationFailed):
        clean_email(bad)
