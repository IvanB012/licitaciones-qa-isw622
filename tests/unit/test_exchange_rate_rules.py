"""Reglas puras del tipo de cambio. El esperado sale de REQ-010 (CLAUDE.md) y del contrato §5."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.errors import ValidationFailed
from app.exchange import ExchangeRateUnavailable, HttpExchangeRateProvider
from app.rules.exchange_rates import check_source, parse_rate_date, parse_rate_x10000

NOW = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)  # 06:00 en Costa Rica -> fecha oficial 2026-11-26


@pytest.mark.parametrize("text, expected", [("500.00", 5_000_000), ("500", 5_000_000), ("512.3456", 5_123_456), ("0.0001", 1)])
def test_tasa_valida(text, expected):  # CP-### / REQ-010
    assert parse_rate_x10000(text) == expected


@pytest.mark.parametrize("bad", ["0", "0.00", "-1", "-500.00", "abc", "", "  ", "5e2", "500,00", "500.12345", "1.2.3", None, 500, 500.0])
def test_tasa_invalida_422(bad):  # CP-### / REQ-010
    with pytest.raises(ValidationFailed) as exc:
        parse_rate_x10000(bad)
    assert exc.value.code == "tasa_invalida" and exc.value.status == 422


def test_tasa_demasiado_grande_no_revienta_la_bd():  # CP-### / REQ-010
    with pytest.raises(ValidationFailed) as exc:
        parse_rate_x10000("999999999999999")  # x10 000 no cabe en 64 bits
    assert exc.value.code == "tasa_invalida"


def test_fecha_por_defecto_es_la_oficial():  # CP-### / REQ-010
    assert parse_rate_date(None, NOW) == date(2026, 11, 26)
    assert parse_rate_date("  ", NOW) == date(2026, 11, 26)


def test_fecha_oficial_usa_hora_de_costa_rica():  # CP-### / REQ-010
    tarde_utc = datetime(2026, 11, 27, 3, 0, tzinfo=timezone.utc)  # 21:00 del 26 en CR
    assert parse_rate_date(None, tarde_utc) == date(2026, 11, 26)
    assert parse_rate_date("2026-11-26", tarde_utc) == date(2026, 11, 26)


@pytest.mark.parametrize("bad", ["2026-11-25", "2026-11-27", "26/11/2026", "no-es-fecha", 20261126])
def test_fecha_distinta_de_la_oficial_422(bad):  # CP-### / REQ-010
    with pytest.raises(ValidationFailed) as exc:
        parse_rate_date(bad, NOW)
    assert exc.value.code == "tasa_invalida"


def test_al_editar_se_admite_conservar_la_fecha_anterior():  # CP-### / REQ-010
    assert parse_rate_date("2026-11-20", NOW, existing=date(2026, 11, 20)) == date(2026, 11, 20)


def test_fuente_solo_manual_o_sugerida():  # CP-### / REQ-010
    assert check_source(None) == "manual" and check_source("sugerida") == "sugerida"
    for bad in ("seed", "externo", "otra", 5):
        with pytest.raises(ValidationFailed):
            check_source(bad)


# ---- proveedor HTTP: cualquier fallo -> ExchangeRateUnavailable (sin red real: respuestas simuladas) ----
class _Resp:
    def __init__(self, payload=None, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.mark.parametrize(
    "resp",
    [_Resp({"rates": {"CRC": 502.5}}, 500), _Resp({"rates": {}}), _Resp({}), _Resp(ValueError("no json")),
     _Resp({"rates": {"CRC": "abc"}}), _Resp({"rates": {"CRC": 0}}), _Resp({"rates": {"CRC": -3}}), _Resp([1])],
)
def test_proveedor_http_fallos_son_no_disponible(monkeypatch, resp):  # CP-### / REQ-010
    monkeypatch.setattr("app.exchange.httpx.get", lambda *a, **k: resp)
    with pytest.raises(ExchangeRateUnavailable):
        HttpExchangeRateProvider("http://ejemplo.invalido").get_rate()


def test_proveedor_http_error_de_red_es_no_disponible(monkeypatch):  # CP-### / REQ-010
    import httpx

    def boom(*a, **k):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr("app.exchange.httpx.get", boom)
    with pytest.raises(ExchangeRateUnavailable):
        HttpExchangeRateProvider().get_rate()


def test_proveedor_http_lee_rates_crc_con_timeout_de_3s(monkeypatch):  # CP-### / REQ-010
    seen = {}

    def fake_get(url, timeout):
        seen.update(url=url, timeout=timeout)
        return _Resp({"rates": {"CRC": 512.34}})

    monkeypatch.setattr("app.exchange.httpx.get", fake_get)
    assert HttpExchangeRateProvider("http://ejemplo.invalido/x").get_rate() == Decimal("512.34")
    assert seen == {"url": "http://ejemplo.invalido/x", "timeout": 3.0}
