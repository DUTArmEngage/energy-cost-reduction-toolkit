"""Time-of-Use tariff: which period a moment falls in, and what a kWh costs then.

The rates and time bands below are PLACEHOLDERS to exercise the UI, not a real tariff. Replace them with the tariff you are on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

PERIODS = ("peak", "standard", "off-peak")

# (start hour inclusive, end hour exclusive) per period
WEEKDAY = {"peak": [(7, 10), (18, 20)], "standard": [(6, 7), (10, 18), (20, 22)]}
WEEKEND = {"standard": [(7, 12), (18, 20)]}


@dataclass
class Tariff:
    rates: dict[str, float] = field(default_factory=lambda: {"peak": 3.00, "standard": 1.80, "off-peak": 1.10})   # R per kWh

    def period_at(self, when: datetime) -> str:
        bands = WEEKDAY if when.weekday() < 5 else WEEKEND
        for period, spans in bands.items():
            if any(a <= when.hour < b for a, b in spans):
                return period
        return "off-peak"

    def rate_at(self, when: datetime) -> float:
        return self.rates[self.period_at(when)]
