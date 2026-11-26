"""Reglas puras de proveedores (REQ-001, REQ-012). Sin BD ni red."""
import re
import unicodedata

from app.errors import ValidationFailed
from app.rules.normalization import compact_spaces

NAME_PUNCTUATION = ".,()"  # REQ-012: además de letras, dígitos y espacio
NAME_ERROR = "El nombre solo admite letras (con tildes y ñ), números, espacios, punto, coma y paréntesis."
NAME_REQUIRED = "El nombre del proveedor es obligatorio."
EMAIL_ERROR = "El correo de contacto no es válido."
_PART = r"[^@\s<>\"'(),;:\\]+"
_EMAIL = re.compile(rf"^{_PART}@{_PART}\.{_PART}$")


def clean_name(name: object) -> str:
    """Nombre válido y saneado (REQ-001/012): NFC, recortado y con espacios internos compactados.

    Se rechaza: no texto, vacío tras recortar, o cualquier carácter que no sea letra Unicode, dígito,
    espacio simple, punto, coma o paréntesis (tabuladores, saltos de línea, `<`, `&`, `;`, emojis...).
    """
    if not isinstance(name, str):
        raise ValidationFailed(NAME_REQUIRED, code="validacion_nombre")
    text = unicodedata.normalize("NFC", name).strip()
    if not text:
        raise ValidationFailed(NAME_REQUIRED, code="validacion_nombre")
    if not all(ch.isalpha() or ch.isdecimal() or ch == " " or ch in NAME_PUNCTUATION for ch in text):
        raise ValidationFailed(NAME_ERROR, code="validacion_nombre")
    return compact_spaces(text)


def clean_email(email: object) -> str | None:
    """Correo de contacto opcional: None si viene vacío; formato simple usuario@dominio.ext si viene."""
    if email is None:
        return None
    if not isinstance(email, str):
        raise ValidationFailed(EMAIL_ERROR, code="validacion")
    email = email.strip()
    if not email:
        return None
    if not _EMAIL.match(email):
        raise ValidationFailed(EMAIL_ERROR, code="validacion")
    return email
