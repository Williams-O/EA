"""Load/save candles from local CSV files, including MetaTrader exports."""
from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Sequence

import pandas as pd

from .instrument import SymbolSpec
from .models import Timeframe
from .validation import DataQualityReport, validate_candles

COLUMNS = ["open", "high", "low", "close", "volume", "spread"]


def _timestamp_to_utc(value: datetime, source_tz: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        try:
            ts = ts.tz_localize(source_tz, ambiguous="raise", nonexistent="raise")
        except Exception as exc:
            raise ValueError(
                f"Cannot interpret naive timestamp in {source_tz!r}; ambiguous/nonexistent "
                "local time. Use an explicit timezone or fixed offset."
            ) from exc
    return ts.tz_convert("UTC")


class CsvCandleProvider:
    """Read `<data_dir>/<SYMBOL>_<TIMEFRAME>.csv`.

    Supports ordinary comma-separated CSVs and tab-delimited MT5 exports. Naive times
    are interpreted in source_tz; aware timestamps are converted to UTC. MT5 tick-volume
    is preferred over real volume because CFD/OTC feeds may report real volume as zero.
    Missing spread stays NaN (unknown cost), never zero. MT5 spread values are points
    when spread_in_points=True and a SymbolSpec is supplied.
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
        source_tz: str = "UTC",
        spec: SymbolSpec | None = None,
        spread_in_points: bool = False,
        daily_breaks: Sequence[tuple[time, time]] = (),
        max_range_pct: float | None = None,
    ) -> None:
        if spread_in_points and spec is None:
            raise ValueError("spread_in_points=True requires a SymbolSpec (point size).")
        self.data_dir = Path(data_dir)
        self.source_tz = source_tz
        self.spec = spec
        self.spread_in_points = spread_in_points
        self.daily_breaks = tuple(daily_breaks)
        self.max_range_pct = max_range_pct
        self.last_report: DataQualityReport | None = None

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        symbol = symbol.strip().upper()
        if not isinstance(timeframe, Timeframe):
            raise TypeError("timeframe must be a Timeframe enum.")
        if self.spec is not None and self.spec.symbol != symbol:
            raise ValueError(f"Spec is for {self.spec.symbol}, but {symbol} was requested.")
        path = self.data_dir / f"{symbol}_{timeframe.name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"No data file: {path}")

        header = path.read_text(encoding="utf-8-sig").splitlines()[0]
        delimiter = "\t" if "\t" in header else ","
        raw = pd.read_csv(path, sep=delimiter, engine="python", encoding="utf-8-sig")
        raw.columns = [str(c).strip().strip("<>").lower().replace(" ", "_") for c in raw.columns]
        aliases = {
            "tickvol": "tick_volume",
            "tick_volume": "tick_volume",
            "tickvolume": "tick_volume",
            "real_volume": "real_volume",
            "vol": "real_volume",
        }
        raw = raw.rename(columns=aliases)

        if "date" in raw.columns and "time" in raw.columns:
            stamps = raw["date"].astype(str).str.strip() + " " + raw["time"].astype(str).str.strip()
        elif "time" in raw.columns:
            stamps = raw["time"]
        else:
            raise ValueError("CSV must contain 'time' or MT5 'date' and 'time' columns.")
        parsed = pd.to_datetime(stamps, errors="coerce")
        if parsed.isna().any():
            raise ValueError(f"{int(parsed.isna().sum())} unparseable timestamps in {path.name}.")
        try:
            if parsed.dt.tz is None:
                parsed = parsed.dt.tz_localize(self.source_tz, ambiguous="raise", nonexistent="raise")
            parsed = parsed.dt.tz_convert("UTC")
        except Exception as exc:
            raise ValueError(
                f"Ambiguous or nonexistent local time; could not convert timestamps from "
                f"{self.source_tz!r} to UTC. Check broker timezone and DST ambiguity."
            ) from exc
        raw.index = pd.DatetimeIndex(parsed, name="time")

        # Tick volume is preferred when an MT5 export contains both volume columns.
        if "tick_volume" in raw.columns:
            raw["volume"] = raw["tick_volume"]
        elif "real_volume" in raw.columns:
            raw["volume"] = raw["real_volume"]
        for col in COLUMNS:
            if col not in raw.columns:
                raw[col] = float("nan") if col == "spread" else 0.0
        df = raw[COLUMNS].apply(pd.to_numeric, errors="coerce")
        if self.spread_in_points:
            df["spread"] = df["spread"] * self.spec.point

        df, self.last_report = validate_candles(
            df,
            timeframe,
            daily_breaks=self.daily_breaks,
            min_price=self.spec.min_price if self.spec else None,
            max_price=self.spec.max_price if self.spec else None,
            max_range_pct=self.max_range_pct,
        )

        start_utc = _timestamp_to_utc(start, self.source_tz) if start is not None else None
        end_utc = _timestamp_to_utc(end, self.source_tz) if end is not None else None
        if start_utc is not None and end_utc is not None and start_utc >= end_utc:
            raise ValueError("start must be earlier than end.")
        if start_utc is not None:
            df = df[df.index >= start_utc]
        if end_utc is not None:
            df = df[df.index < end_utc]
        return df


def save_candles_csv(df: pd.DataFrame, path: str | Path) -> Path:
    """Persist locally; keep market-data files out of version control."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index_label="time")
    return path
