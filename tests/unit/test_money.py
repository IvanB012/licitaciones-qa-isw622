from decimal import Decimal

import pytest

from app.errors import ValidationFailed
from app.rules.money import (
    crc_to_usd,
    format_display,
    format_money,
    parse_money,
    parse_rate,
    rate_from_x10000,
    rate_to_x10000,
)


# ---- parse_money: válidos y bordes (REQ-005, REQ-011) ----
@pytest.mark.parametrize(
    "text, cents",
    [
        ("9000000.00", 900_000_000),
        ("0.01", 1),  # mínimo positivo
        ("0.00", 0),  # se parsea; que 0 sea inválido lo decide la regla del módulo
        ("10", 1_000),
        ("10.5", 1_050),
        ("1000000.00", 100_000_000),
        ("999999.99", 99_999_999),
        ("  25.00  ", 2_500),  # espacios en los extremos se toleran
        ("007.10", 710),
        ("-1", -100),  # el signo se parsea; el módulo rechaza <= 0
    ],
)
def test_parse_money_validos(text, cents):
    assert parse_money(text) == cents


@pytest.mark.parametrize(
    "bad",
    [
        "1e3", "1E3", "1,5", "1.000,50", "1000000.001", "0.001", "", "   ", "1 000.00", "1 0",
        "abc", "12abc", "NaN", "inf", ".5", "5.", "+5", "--5", "1_000", "1.2.3", "١٢٣",
        "1" * 16,
    ],
)
def test_parse_money_rechaza_formato_invalido(bad):
    with pytest.raises(ValidationFailed) as exc:
        parse_money(bad)
    assert exc.value.code == "monto_invalido" and exc.value.status == 422


@pytest.mark.parametrize("bad", [1000.5, 1000, None, Decimal("1.00"), ["1"], True])
def test_parse_money_rechaza_no_strings(bad):
    with pytest.raises(ValidationFailed) as exc:
        parse_money(bad)
    assert exc.value.code == "monto_invalido"


def test_parse_money_un_centimo_sobre_presupuesto_se_distingue():
    assert parse_money("1000000.01") - parse_money("1000000.00") == 1


# ---- format_money ----
@pytest.mark.parametrize(
    "cents, text",
    [(900_000_000, "9000000.00"), (1, "0.01"), (0, "0.00"), (99_999_999, "999999.99"), (-150, "-1.50"), (1_050, "10.50")],
)
def test_format_money(cents, text):
    assert format_money(cents) == text


@pytest.mark.parametrize("cents", [0, 1, 99, 100, 1_050, 999_999_999_999_999_99, -1])
def test_ida_y_vuelta(cents):
    assert parse_money(format_money(cents)) == cents


@pytest.mark.parametrize("bad", [1.5, "100", None, True])
def test_format_money_exige_int(bad):
    with pytest.raises(TypeError):
        format_money(bad)


# ---- crc_to_usd (REQ-010) ----
def test_crc_a_usd_ejemplo_del_seed():
    assert crc_to_usd(900_000_000, Decimal("500.00")) == Decimal("18000.00")


@pytest.mark.parametrize(
    "cents, rate, expected",
    [
        (100_000_000, Decimal("500"), "2000.00"),
        (1, Decimal("500"), "0.00"),  # 0.01 CRC / 500
        (25_000, Decimal("500"), "0.50"),  # 250 CRC
        (50_000, Decimal("400"), "1.25"),
        (1_000, Decimal("400"), "0.03"),  # 10/400 = 0.025 -> half up -> 0.03
        (1_000, Decimal("600"), "0.02"),  # 0.01666 -> 0.02
        (0, Decimal("500"), "0.00"),
    ],
)
def test_crc_a_usd_redondeo_half_up(cents, rate, expected):
    assert crc_to_usd(cents, rate) == Decimal(expected)


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-500"), 0, Decimal("NaN"), Decimal("Infinity"), 500.0, None, "500"])
def test_crc_a_usd_exige_tasa_positiva(rate):
    with pytest.raises(ValidationFailed) as exc:
        crc_to_usd(100_000, rate)
    assert exc.value.code == "tasa_invalida"


def test_crc_a_usd_no_modifica_entrada():
    cents = 900_000_000
    crc_to_usd(cents, Decimal("500"))
    assert cents == 900_000_000


# ---- format_display ----
def test_format_display_crc():
    assert format_display(900_000_000, "CRC") == "₡9 000 000,00"
    assert format_display(1, "CRC") == "₡0,01"
    assert format_display(0, "CRC") == "₡0,00"
    assert format_display(99_999_999, "crc") == "₡999 999,99"
    assert format_display(-150, "CRC") == "₡-1,50"


def test_format_display_usd():
    assert format_display(900_000_000, "USD", Decimal("500.00")) == "$18 000,00"
    assert format_display(1_000_000_000, "USD", Decimal("500")) == "$20 000,00"


def test_format_display_usd_sin_tasa_o_con_tasa_invalida():
    for rate in (None, Decimal("0"), Decimal("-1")):
        with pytest.raises(ValidationFailed) as exc:
            format_display(100, "USD", rate)
        assert exc.value.code == "tasa_invalida"


def test_format_display_moneda_desconocida():
    with pytest.raises(ValueError):
        format_display(100, "EUR")


def test_filtro_jinja_format_display_registrado():
    from app.web.templating import templates

    out = templates.env.from_string("{{ c | format_display('USD', r) }}").render(c=900_000_000, r=Decimal("500"))
    assert out == "$18 000,00"


# ---- parse_rate / rate_x10000 ----
@pytest.mark.parametrize("text, rate", [("500", "500"), ("500.00", "500.00"), ("512.3456", "512.3456"), (" 0.01 ", "0.01")])
def test_parse_rate_validos(text, rate):
    assert parse_rate(text) == Decimal(rate)


@pytest.mark.parametrize(
    "bad", ["0", "0.00", "-1", "-500.00", "1e3", "1,5", "500.12345", "", " ", "5 00", "abc", "NaN", "Infinity", ".5", 500.0, 500, None]
)
def test_parse_rate_rechaza(bad):
    with pytest.raises(ValidationFailed) as exc:
        parse_rate(bad)
    assert exc.value.code == "tasa_invalida" and exc.value.status == 422


def test_rate_x10000_ida_y_vuelta():
    assert rate_to_x10000(Decimal("500.00")) == 5_000_000
    assert rate_to_x10000(parse_rate("512.3456")) == 5_123_456
    assert rate_from_x10000(5_000_000) == Decimal("500")
    assert rate_from_x10000(5_123_456) == Decimal("512.3456")


def test_rate_to_x10000_redondea_half_up_y_exige_positiva():
    assert rate_to_x10000(Decimal("500.12345")) == 5_001_235  # tasa del proveedor externo con más decimales
    for bad in (Decimal("0"), Decimal("-1")):
        with pytest.raises(ValidationFailed):
            rate_to_x10000(bad)
    with pytest.raises(ValidationFailed):
        rate_to_x10000(Decimal("0.00001"))  # se redondearía a 0
