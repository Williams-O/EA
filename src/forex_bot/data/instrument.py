"""Broker-verified instrument specification.

Gold specifications are broker-specific. Example values are illustrative only; verify
symbol digits, tick/point size, contract size, volume limits and price bounds with the broker.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

_REQUIRED = ("symbol", "digits", "point", "contract_size", "volume_min", "volume_step", "volume_max")
_OPTIONAL = ("min_price", "max_price")


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    digits: int
    point: float
    contract_size: float
    volume_min: float
    volume_step: float
    volume_max: float
    min_price: float | None = None
    max_price: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if not self.symbol:
            raise ValueError("symbol must not be empty.")
        if isinstance(self.digits, bool) or not isinstance(self.digits, int) or self.digits < 0:
            raise ValueError("digits must be a non-negative integer.")
        for name in ("point", "contract_size", "volume_min", "volume_step", "volume_max"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number.")
        if self.volume_min > self.volume_max:
            raise ValueError("volume_min must not exceed volume_max.")
        for name in ("min_price", "max_price"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not math.isfinite(value) or value <= 0):
                raise ValueError(f"{name} must be finite and positive when provided.")
        if self.min_price is not None and self.max_price is not None:
            if self.min_price >= self.max_price:
                raise ValueError("min_price must be below max_price.")

    def round_price(self, price: float) -> float:
        """Round to the broker's point increment, then return a float."""
        if not math.isfinite(price) or price <= 0:
            raise ValueError("price must be finite and positive.")
        tick = Decimal(str(self.point))
        price_decimal = Decimal(str(price))
        ticks = (price_decimal / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return float(ticks * tick)

    def points_to_price(self, points: float) -> float:
        """Convert broker points (such as MT5 spread) to quote-price units."""
        if not math.isfinite(points):
            raise ValueError("points must be finite.")
        return points * self.point


def load_symbol_spec(path: str | Path) -> SymbolSpec:
    """Load JSON. Missing/unknown keys are rejected; values are not broker-verified."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Symbol spec JSON must contain an object.")
    missing = [k for k in _REQUIRED if k not in data]
    unknown = [k for k in data if k not in _REQUIRED + _OPTIONAL]
    if missing:
        raise ValueError(f"Symbol spec missing keys: {missing}")
    if unknown:
        raise ValueError(f"Symbol spec has unknown keys: {unknown}")
    return SymbolSpec(**data)
