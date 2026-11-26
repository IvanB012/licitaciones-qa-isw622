"""Dinero (contrato §1 y §7). Funciones PURAS: sin BD, sin red, sin float.

CRC se maneja siempre en céntimos (int); la API intercambia strings decimales ("9000000.00").
Aquí solo se valida el FORMATO. El rango (> 0, <= presupuesto) lo validan las reglas de cada módulo.
"""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.errors import ValidationFailed

CODE_MONEY = "monto_invalido"
CODE_RATE = "tasa_invalida"

MAX_INTEGER_DIGITS = 15  # tope razonable (< límite de BIGINT en céntimos)
_MONEY_RE = re.compile(r"-?[0-9]{1,%d}(?:\.[0-9]{1,2})?" % MAX_INTEGER_DIGITS)
_RATE_RE = re.compile(r"[0-9]{1,%d}(?:\.[0-9]{1,4})?" % MAX_INTEGER_DIGITS)  # hasta 4 decimales = precisión de rate_x10000

_CENT = Decimal("0.01")
_RATE_STEP = Decimal("0.0001")
SYMBOLS = {"CRC": "₡", "USD": "$"}


def _clean(text: object, code: str, what: str) -> str:
    if not isinstance(text, str):  # float, int, None, Decimal... se rechazan: la API manda strings
        raise ValidationFailed(f"{what} debe enviarse como texto decimal (ej. \"1500.00\").", code=code)
    return text.strip()


def parse_money(text: str) -> int:
    """Texto decimal -> céntimos (int).

    Acepta: "9000000.00", "0.01", "10", "10.5", "-1" (el signo "-" se parsea; que sea inválido por
    ser <= 0 lo decide la regla del módulo). Rechaza (ValidationFailed ``monto_invalido``): float,
    notación científica ("1e3"), coma decimal ("1,5"), más de 2 decimales ("1000000.001"), vacío,
    espacios internos, "+", ".5", "5.", separadores de miles y cualquier no numérico.
    Se toleran espacios en los extremos.
    """
    value = _clean(text, CODE_MONEY, "El monto")
    if not _MONEY_RE.fullmatch(value):
        raise ValidationFailed(
            "Monto inválido: use solo dígitos con punto decimal y hasta 2 decimales (ej. 1500.00).",
            code=CODE_MONEY,
        )
    return int(Decimal(value) * 100)


def _check_cents(cents: object) -> int:
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError("los céntimos deben ser int")
    return cents


def format_money(cents: int) -> str:
    """Céntimos -> string decimal con 2 decimales: 900000000 -> "9000000.00"."""
    cents = _check_cents(cents)
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"


def _check_rate(rate: object) -> Decimal:
    if isinstance(rate, bool) or not isinstance(rate, (Decimal, int)):
        raise ValidationFailed("La tasa debe ser un número decimal mayor que cero.", code=CODE_RATE)
    rate = Decimal(rate)
    if not rate.is_finite() or rate <= 0:
        raise ValidationFailed("La tasa debe ser mayor que cero.", code=CODE_RATE)
    return rate


def crc_to_usd(cents: int, rate: Decimal) -> Decimal:
    """CRC (céntimos) -> USD con ROUND_HALF_UP a 2 decimales (REQ-010). Exige tasa > 0.

    crc_to_usd(900_000_000, Decimal("500.00")) == Decimal("18000.00")
    """
    cents = _check_cents(cents)
    rate = _check_rate(rate)
    return (Decimal(cents) / 100 / rate).quantize(_CENT, rounding=ROUND_HALF_UP)


def _group(cents: int) -> str:
    """Formato de visualización: miles separados por espacio, coma decimal (1 000 000,00)."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}".replace(",", " ") + f",{frac:02d}"


def format_display(cents: int, currency: str = "CRC", rate: Decimal | None = None) -> str:
    """Texto para la UI. CRC: "₡9 000 000,00". USD: convierte con la tasa -> "$18 000,00".

    Solo es presentación: nunca modifica lo persistido (REQ-010). USD exige ``rate`` > 0.
    """
    cents = _check_cents(cents)
    code = (currency or "").upper()
    if code not in SYMBOLS:
        raise ValueError(f"moneda no soportada: {currency!r}")
    if code == "CRC":
        return f"{SYMBOLS['CRC']}{_group(cents)}"
    usd = crc_to_usd(cents, rate) if rate is not None else _check_rate(rate)  # rate None -> tasa_invalida
    return f"{SYMBOLS['USD']}{_group(int(usd * 100))}"


def parse_rate(text: str) -> Decimal:
    """Texto -> tasa CRC por USD (Decimal > 0), con el mismo rigor de formato que parse_money.

    Hasta 4 decimales (la precisión de ``rate_x10000``). Rechaza (``tasa_invalida``) formato
    inválido, cero y negativos (una tasa solo existe si es > 0).
    """
    value = _clean(text, CODE_RATE, "La tasa")
    if not _RATE_RE.fullmatch(value):
        raise ValidationFailed(
            "Tasa inválida: use solo dígitos con punto decimal y hasta 4 decimales (ej. 500.00).",
            code=CODE_RATE,
        )
    return _check_rate(Decimal(value))


def rate_to_x10000(rate: Decimal) -> int:
    """Tasa -> entero persistido (500.00 -> 5_000_000). Redondea ROUND_HALF_UP a 4 decimales."""
    rate = _check_rate(rate)
    scaled = int((rate.quantize(_RATE_STEP, rounding=ROUND_HALF_UP) * 10000).to_integral_value())
    if scaled <= 0:
        raise ValidationFailed("La tasa es demasiado pequeña.", code=CODE_RATE)
    return scaled


def rate_from_x10000(value: int) -> Decimal:
    """Entero persistido -> tasa Decimal (5_000_000 -> Decimal("500.0000"))."""
    return Decimal(_check_cents(value)) / 10000
