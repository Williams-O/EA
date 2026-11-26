"""Data-quality checks for candle DataFrames."""
from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import time
from typing import Sequence

import pandas as pd

from .models import Timeframe

REQUIRED = ["open", "high", "low", "close"]
NUMERIC = REQUIRED + ["volume", "spread"]


@dataclass
class DataQualityReport:
    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    conflicting_duplicates: int = 0
    out_of_order: int = 0
    invalid_rows_removed: int = 0
    out_of_bounds_removed: int = 0
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=list)
    suspicious_ranges: list[pd.Timestamp] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.duplicates_removed == 0
            and self.conflicting_duplicates == 0
            and self.out_of_order == 0
            and self.invalid_rows_removed == 0
            and self.out_of_bounds_removed == 0
            and not self.gaps
            and not self.suspicious_ranges
        )


def _is_weekend_gap(start: pd.Timestamp, end: pd.Timestamp) -> bool:
    """Conservative UTC heuristic, NOT a broker session calendar.

    Only suppresses a Friday >=16:00 UTC to Sunday >=16:00 UTC gap (<=72h).
    Broker sessions vary and shift with DST; this can still mask missing data.
    """
    return (
        start.weekday() == 4
        and end.weekday() == 6
        and start.hour >= 16
        and end.hour >= 16
        and (end - start) <= pd.Timedelta(hours=72)
    )


def _in_daily_break(
    missing_start: pd.Timestamp,
    missing_end: pd.Timestamp,
    breaks: Sequence[tuple[time, time]],
) -> bool:
    if missing_start.date() != missing_end.date():
        return False
    return any(
        b_start <= missing_start.time() and missing_end.time() <= b_end
        for b_start, b_end in breaks
    )


def validate_candles(
    df: pd.DataFrame,
    timeframe: Timeframe,
    *,
    daily_breaks: Sequence[tuple[time, time]] = (),
    min_price: float | None = None,
    max_price: float | None = None,
    max_range_pct: float | None = None,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Clean candles and report quality issues; never fills missing candles.

    Index is normalized to UTC. Non-finite OHLC/volume or invalid OHLC structure
    are removed. Missing spread is allowed and remains NaN; negative/infinite spread
    is invalid. Duplicate timestamps are dropped (first kept) and conflicting rows
    are counted. Gap detection is heuristic and should be checked against broker sessions.
    """
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
        raise ValueError("Index must be a timezone-aware DatetimeIndex.")
    if not isinstance(timeframe, Timeframe):
        raise TypeError("timeframe must be a Timeframe enum.")
    if max_range_pct is not None and (not math.isfinite(max_range_pct) or max_range_pct <= 0):
        raise ValueError("max_range_pct must be finite and positive.")
    for name, bound in (("min_price", min_price), ("max_price", max_price)):
        if bound is not None and (not math.isfinite(bound) or bound <= 0):
            raise ValueError(f"{name} must be finite and positive.")
    if min_price is not None and max_price is not None and min_price >= max_price:
        raise ValueError("min_price must be less than max_price.")
    for b_start, b_end in daily_breaks:
        if b_start >= b_end:
            raise ValueError("Each daily break must satisfy start < end (same UTC day).")

    report = DataQualityReport(rows_in=len(df))
    out = df.copy()
    out.index = out.index.tz_convert("UTC")
    out.index.name = df.index.name or "time"

    if "volume" not in out:
        out["volume"] = 0.0
    if "spread" not in out:
        out["spread"] = float("nan")
    for col in NUMERIC:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    report.out_of_order = int((out.index.to_series().diff() < pd.Timedelta(0)).sum())
    out = out.sort_index()

    duplicate_mask = out.index.duplicated(keep=False)
    if duplicate_mask.any():
        for _, group in out.loc[duplicate_mask].groupby(level=0, sort=False):
            comparable = group[NUMERIC]
            first = comparable.iloc[0]
            if any(
                not (first.eq(row) | (first.isna() & row.isna())).all()
                for _, row in comparable.iloc[1:].iterrows()
            ):
                report.conflicting_duplicates += 1
    dup_mask = out.index.duplicated(keep="first")
    report.duplicates_removed = int(dup_mask.sum())
    out = out[~dup_mask]

    prices = out[REQUIRED]
    bad = (
        ~np.isfinite(prices.to_numpy(dtype=float)).all(axis=1)
        | (prices <= 0).any(axis=1)
        | (out["high"] < out[["open", "close", "low"]].max(axis=1))
        | (out["low"] > out[["open", "close", "high"]].min(axis=1))
        | ~out["volume"].map(lambda x: math.isfinite(x) if pd.notna(x) else False)
        | (out["volume"] < 0)
    )
    bad_spread = out["spread"].map(lambda x: pd.notna(x) and (not math.isfinite(x) or x < 0))
    bad |= bad_spread
    report.invalid_rows_removed = int(bad.sum())
    out = out[~bad]

    if min_price is not None or max_price is not None:
        oob = pd.Series(False, index=out.index)
        if min_price is not None:
            oob |= (out[REQUIRED] < min_price).any(axis=1)
        if max_price is not None:
            oob |= (out[REQUIRED] > max_price).any(axis=1)
        report.out_of_bounds_removed = int(oob.sum())
        out = out[~oob]

    if max_range_pct is not None and len(out):
        range_pct = (out["high"] - out["low"]) / out["close"]
        report.suspicious_ranges = list(out.index[range_pct > max_range_pct])

    step = timeframe.delta
    for prev, cur in zip(out.index[:-1], out.index[1:]):
        if cur - prev <= step or _is_weekend_gap(prev, cur):
            continue
        if _in_daily_break(prev + step, cur, daily_breaks):
            continue
        report.gaps.append((prev, cur))

    report.rows_out = len(out)
    return out, report
