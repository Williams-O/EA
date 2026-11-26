"""Provider interface. Brokers/data vendors implement this later."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from .models import Timeframe


class CandleProvider(Protocol):
    """Returns candles as a DataFrame indexed by UTC bar-open time.

    Columns: open, high, low, close, volume, spread.
    Spread is in quote-price units and may be NaN when unknown.
    """

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame: ...
