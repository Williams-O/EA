"""Core market data types."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class Timeframe(Enum):
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440

    @property
    def delta(self) -> timedelta:
        return timedelta(minutes=self.value)

    @classmethod
    def parse(cls, name: str) -> "Timeframe":
        """Parse timeframe names such as M15."""
        try:
            return cls[name.strip().upper()]
        except (KeyError, AttributeError):
            valid = ", ".join(t.name for t in cls)
            raise ValueError(f"Unknown timeframe {name!r}. Valid: {valid}") from None


@dataclass(frozen=True)
class Candle:
    """One OHLCV bar; its open time must be UTC.

    Spread is expressed in quote-price units, not broker points.
    """

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    spread: float | None = None

    def __post_init__(self) -> None:
        if self.time.tzinfo is None or self.time.utcoffset() != timedelta(0):
            raise ValueError("Candle time must be timezone-aware UTC.")
        prices = (self.open, self.high, self.low, self.close)
        if any(not math.isfinite(p) or p <= 0 for p in prices):
            raise ValueError("Candle prices must be finite and positive.")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("High is below open/close/low.")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("Low is above open/close/high.")
        if not math.isfinite(self.volume) or self.volume < 0:
            raise ValueError("Volume must be finite and non-negative.")
        if self.spread is not None and (not math.isfinite(self.spread) or self.spread < 0):
            raise ValueError("Spread must be finite and non-negative when provided.")

    @staticmethod
    def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
