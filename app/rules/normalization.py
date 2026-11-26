"""Normalización de texto (contrato §1). Funciones puras."""
import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"se esperaba str, se recibió {type(value).__name__}")
    return value


def compact_spaces(text: str) -> str:
    """Recorta los extremos y compacta los espacios internos a uno solo.

    Es la forma que se guarda en ``providers.name`` (nombre "original" saneado).
    Considera espacio cualquier blanco Unicode (tabuladores, NBSP, etc.).
    """
    return _WHITESPACE.sub(" ", _require_str(text).strip())


def normalize_name(name: str) -> str:
    """Clave de comparación de nombres de proveedor (REQ-001): ``name_key``.

    Recorta, compacta espacios internos, normaliza Unicode (NFC) y compara sin
    distinguir mayúsculas (``casefold``). Dos nombres equivalentes producen la
    misma clave:  ``"  Tecnología   Norte S.A. "`` -> ``"tecnología norte s.a."``.
    """
    return unicodedata.normalize("NFC", compact_spaces(name)).casefold()


def normalize_code(code: str) -> str:
    """Clave de unicidad del código de licitación (REQ-002): ``code_key``.

    Recorta espacios laterales y compara sin distinguir mayúsculas:
    ``"  lic-2026-001 "`` -> ``"lic-2026-001"``. No altera espacios internos.
    """
    return _require_str(code).strip().casefold()
