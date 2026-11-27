"""Reglas puras de usuarios (contrato §5 Usuarios y §8). Los límites de usuario y contraseña son decisiones del equipo
documentadas en app/rules/users.py; el resto sale del contrato (roles admin/operador)."""
import pytest

from app.errors import ValidationFailed
from app.rules.users import clean_username, validate_active, validate_password, validate_role


# ---- usuario ----
@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("admin", "admin"),
        ("  operador  ", "operador"),  # se recorta
        ("Ana.Mora-01_x", "Ana.Mora-01_x"),
        ("abc", "abc"),  # mínimo: 3
        ("a" * 50, "a" * 50),  # máximo: 50
    ],
)
def test_usuario_valido(texto, esperado):
    assert clean_username(texto) == esperado


@pytest.mark.parametrize(
    "malo",
    ["", "   ", "ab", "a" * 51, "con espacio", "ana@correo", "ana<script>", "ñandú", "a/b", "ana;drop", None, 123, ["x"]],
)
def test_usuario_invalido(malo):
    with pytest.raises(ValidationFailed) as exc:
        clean_username(malo)
    assert exc.value.code == "validacion_usuario" and exc.value.status == 422


# ---- contraseña ----
@pytest.mark.parametrize("clave", ["Admin#2026-test", "12345678", "a" * 8, "a" * 128, "con espacios dentro ok"])
def test_contrasena_valida(clave):
    assert validate_password(clave) == clave  # no se recorta ni se modifica


@pytest.mark.parametrize("mala", ["", "        ", "corta", "1234567", "a" * 129, None, 12345678, ["abcdefgh"]])
def test_contrasena_invalida(mala):
    with pytest.raises(ValidationFailed) as exc:
        validate_password(mala)
    assert exc.value.code == "validacion_clave" and exc.value.status == 422


def test_el_error_de_contrasena_no_repite_el_valor():
    with pytest.raises(ValidationFailed) as exc:
        validate_password("corta")
    assert "corta" not in exc.value.detalle


# ---- rol ----
@pytest.mark.parametrize("rol", ["admin", "operador"])
def test_rol_valido(rol):
    assert validate_role(rol) == rol


@pytest.mark.parametrize("malo", ["superuser", "ADMIN", "", None, 1, ["admin"], {"a": 1}])
def test_rol_invalido(malo):
    with pytest.raises(ValidationFailed) as exc:
        validate_role(malo)
    assert exc.value.code == "validacion_rol"


# ---- activo ----
@pytest.mark.parametrize("valor", [True, False])
def test_activo_valido(valor):
    assert validate_active(valor) is valor


@pytest.mark.parametrize("malo", ["true", "si", 1, 0, None, "on"])
def test_activo_solo_acepta_booleanos(malo):
    with pytest.raises(ValidationFailed) as exc:
        validate_active(malo)
    assert exc.value.code == "validacion_activo"
