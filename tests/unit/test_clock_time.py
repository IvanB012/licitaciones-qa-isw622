from datetime import date, datetime, timedelta, timezone

import pytest

from app.clock import FakeClock, SystemClock
from app.rules.timeutil import official_date, to_cr

UTC = timezone.utc


def test_fake_clock_set_y_advance():
    clock = FakeClock(datetime(2026, 11, 26, 12, 0, tzinfo=UTC))
    cierre = clock.now() + timedelta(hours=48)
    clock.advance(hours=48)
    assert clock.now() == cierre  # "exactamente en el cierre"
    clock.advance(seconds=1)
    assert clock.now() > cierre
    clock.set(datetime(2026, 1, 1, tzinfo=UTC))
    assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)


def test_fake_clock_rechaza_naive():
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 1, 1))


def test_system_clock_devuelve_utc_aware():
    now = SystemClock().now()
    assert now.tzinfo is not None and now.utcoffset() == timedelta(0)


def test_hora_costa_rica_es_utc_menos_6():
    assert to_cr(datetime(2026, 11, 27, 2, 0, tzinfo=UTC)).hour == 20
    # 22:00 CR del 26 = 04:00 UTC del 27: la fecha oficial es la de Costa Rica
    assert official_date(datetime(2026, 11, 27, 4, 0, tzinfo=UTC)) == date(2026, 11, 26)


def test_to_cr_rechaza_naive():
    with pytest.raises(ValueError):
        to_cr(datetime(2026, 1, 1))
