"""Reglas puras de usuarios (contrato §5 Usuarios, §8). Sin BD ni red.

La unicidad del nombre de usuario sin distinguir mayúsculas la comprueba el service (y la respalda la BD).
"""
import re

from app.errors import ValidationFailed
from app.rules.constants import ROLES

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{3,50}")
PASSWORD_MIN = 8
PASSWORD_MAX = 128


def clean_username(value: object) -> str:
    """Usuario recortado: 3 a 50 caracteres entre letras, dígitos, punto, guion y guion bajo (sin espacios)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationFailed("El nombre de usuario es obligatorio.", code="validacion_usuario")
    clean = value.strip()
    if not USERNAME_PATTERN.fullmatch(clean):
        raise ValidationFailed(
            "El usuario debe tener de 3 a 50 caracteres: letras, números, punto, guion o guion bajo (sin espacios).",
            code="validacion_usuario",
        )
    return clean


def validate_password(value: object) -> str:
    """Contraseña de 8 a 128 caracteres, no solo espacios. No se recorta: se guarda tal cual (con hash)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationFailed("La contraseña es obligatoria.", code="validacion_clave")
    if not PASSWORD_MIN <= len(value) <= PASSWORD_MAX:
        raise ValidationFailed(
            f"La contraseña debe tener entre {PASSWORD_MIN} y {PASSWORD_MAX} caracteres.", code="validacion_clave"
        )
    return value


def validate_role(value: object) -> str:
    if value not in ROLES:  # también rechaza tipos no hashables o no texto
        raise ValidationFailed(f"Rol inválido. Valores permitidos: {', '.join(ROLES)}.", code="validacion_rol")
    return value  # type: ignore[return-value]


def validate_active(value: object) -> bool:
    """``active`` solo acepta true/false reales (no 'si', 1 ni textos)."""
    if not isinstance(value, bool):
        raise ValidationFailed("El campo activo debe ser verdadero o falso.", code="validacion_activo")
    return value
