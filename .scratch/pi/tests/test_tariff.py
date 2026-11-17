from datetime import datetime

from ecrt_pi_scratch.tariff import Tariff


def test_weekday_periods():
    t = Tariff()
    assert t.period_at(datetime(2026, 11, 16, 8, 0)) == "peak"        # Monday morning
    assert t.period_at(datetime(2026, 11, 16, 19, 59)) == "peak"
    assert t.period_at(datetime(2026, 11, 16, 12, 0)) == "standard"
    assert t.period_at(datetime(2026, 11, 16, 23, 0)) == "off-peak"
    assert t.period_at(datetime(2026, 11, 16, 3, 0)) == "off-peak"


def test_weekend_has_no_peak():
    t = Tariff()
    assert t.period_at(datetime(2026, 11, 21, 8, 0)) == "standard"    # Saturday
    assert t.period_at(datetime(2026, 11, 21, 15, 0)) == "off-peak"


def test_rate_follows_period():
    t = Tariff(rates={"peak": 9.0, "standard": 5.0, "off-peak": 1.0})
    assert t.rate_at(datetime(2026, 11, 16, 8, 0)) == 9.0
    assert t.rate_at(datetime(2026, 11, 16, 23, 0)) == 1.0
