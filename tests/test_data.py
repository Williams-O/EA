import json
from datetime import time

import pandas as pd
import pytest

from forex_bot.data import (
    Candle,
    CsvCandleProvider,
    SymbolSpec,
    Timeframe,
    load_symbol_spec,
    save_candles_csv,
    validate_candles,
)

# Synthetic fixture values only; not broker specifications.
GOLD = dict(
    symbol="xauusd", digits=2, point=0.01, contract_size=100,
    volume_min=0.01, volume_step=0.01, volume_max=100, min_price=500, max_price=10000,
)


def make_df(times, base=2650.0):
    n = len(times)
    index = pd.DatetimeIndex(times)
    index = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    return pd.DataFrame(
        {
            "open": [base] * n,
            "high": [base + 2] * n,
            "low": [base - 2] * n,
            "close": [base + 1] * n,
            "volume": [100.0] * n,
        },
        index=index,
    )


def test_candle_rejects_naive_time():
    from datetime import datetime
    with pytest.raises(ValueError, match="timezone-aware"):
        Candle(datetime(2024, 1, 1), 2650, 2655, 2645, 2650)


def test_candle_rejects_bad_ohlc():
    with pytest.raises(ValueError):
        Candle(Candle.utc(2024, 1, 1), 2650, 2640, 2645, 2650)


def test_candle_rejects_infinite_values_and_bad_spread():
    with pytest.raises(ValueError, match="finite"):
        Candle(Candle.utc(2024, 1, 1), 2650, float("inf"), 2645, 2650)
    with pytest.raises(ValueError, match="Spread"):
        Candle(Candle.utc(2024, 1, 1), 2650, 2655, 2645, 2650, spread=float("inf"))


def test_timeframe_parse():
    assert Timeframe.parse(" m15 ") is Timeframe.M15
    with pytest.raises(ValueError, match="Unknown timeframe"):
        Timeframe.parse("M7")


def test_spec_normalizes_and_converts():
    spec = SymbolSpec(**GOLD)
    assert spec.symbol == "XAUUSD"
    assert spec.points_to_price(25) == pytest.approx(0.25)
    assert spec.round_price(2650.12345) == 2650.12


def test_spec_rejects_bad_values():
    with pytest.raises(ValueError):
        SymbolSpec(**{**GOLD, "point": 0})
    with pytest.raises(ValueError):
        SymbolSpec(**{**GOLD, "volume_min": 5, "volume_max": 1})


def test_spec_rejects_nonfinite_and_bad_price_bounds():
    with pytest.raises(ValueError, match="finite positive"):
        SymbolSpec(**{**GOLD, "point": float("nan")})
    with pytest.raises(ValueError, match="min_price"):
        SymbolSpec(**{**GOLD, "min_price": float("inf")})


def test_load_spec_fails_closed(tmp_path):
    good = tmp_path / "ok.json"
    good.write_text(json.dumps(GOLD))
    assert load_symbol_spec(good).digits == 2
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({k: v for k, v in GOLD.items() if k != "point"}))
    with pytest.raises(ValueError, match="missing"):
        load_symbol_spec(bad)
    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps({**GOLD, "pip_value": 10}))
    with pytest.raises(ValueError, match="unknown"):
        load_symbol_spec(extra)


def test_clean_data_is_ok():
    times = pd.date_range("2024-01-02 00:00", periods=5, freq="15min")
    _, report = validate_candles(make_df(times), Timeframe.M15)
    assert report.ok and report.rows_out == 5


def test_duplicates_and_order_fixed():
    times = pd.to_datetime(
        ["2024-01-02 00:15", "2024-01-02 00:00", "2024-01-02 00:15", "2024-01-02 00:30"]
    )
    out, report = validate_candles(make_df(times), Timeframe.M15)
    assert report.duplicates_removed == 1 and report.out_of_order >= 1
    assert out.index.is_monotonic_increasing and len(out) == 3


def test_conflicting_duplicate_is_reported():
    times = pd.to_datetime(["2024-01-02 00:00", "2024-01-02 00:00", "2024-01-02 00:15"])
    df = make_df(times)
    df.iloc[1, df.columns.get_loc("close")] = 2659
    out, report = validate_candles(df, Timeframe.M15)
    assert report.duplicates_removed == 1
    assert report.conflicting_duplicates == 1
    assert not report.ok


def test_invalid_rows_removed():
    times = pd.date_range("2024-01-02", periods=3, freq="15min")
    df = make_df(times)
    df.iloc[1, df.columns.get_loc("high")] = 2640.0
    df.iloc[2, df.columns.get_loc("close")] = float("nan")
    out, report = validate_candles(df, Timeframe.M15)
    assert report.invalid_rows_removed == 2 and len(out) == 1


def test_validator_normalizes_timezone_and_rejects_infinite_values():
    times = pd.date_range("2024-01-02", periods=3, freq="15min", tz="Europe/London")
    df = make_df(times)
    out, report = validate_candles(df, Timeframe.M15)
    assert str(out.index.tz) == "UTC"
    df.iloc[1, df.columns.get_loc("high")] = float("inf")
    out, report = validate_candles(df, Timeframe.M15)
    assert report.invalid_rows_removed == 1 and len(out) == 2


def test_validator_rejects_negative_or_infinite_spread():
    times = pd.date_range("2024-01-02", periods=3, freq="15min")
    df = make_df(times)
    df["spread"] = [0.2, -0.1, float("inf")]
    out, report = validate_candles(df, Timeframe.M15)
    assert report.invalid_rows_removed == 2 and len(out) == 1


def test_price_bounds_remove_bad_ticks():
    times = pd.date_range("2024-01-02", periods=3, freq="15min")
    df = make_df(times)
    df.iloc[1] = [26.5, 26.7, 26.3, 26.6, 100.0]
    out, report = validate_candles(df, Timeframe.M15, min_price=500, max_price=10000)
    assert report.out_of_bounds_removed == 1 and len(out) == 2
    assert not report.ok


def test_suspicious_range_reported_not_removed():
    times = pd.date_range("2024-01-02", periods=3, freq="15min")
    df = make_df(times)
    df.iloc[1, df.columns.get_loc("high")] = 2750.0
    out, report = validate_candles(df, Timeframe.M15, max_range_pct=0.02)
    assert len(out) == 3 and len(report.suspicious_ranges) == 1


def test_gap_weekend_and_daily_break():
    gap = pd.to_datetime(["2024-01-02 00:00", "2024-01-02 01:00"])
    _, report = validate_candles(make_df(gap), Timeframe.M15)
    assert len(report.gaps) == 1
    weekend = pd.to_datetime(["2024-01-05 21:45", "2024-01-07 23:00"], utc=True)
    _, report = validate_candles(make_df(weekend), Timeframe.M15)
    assert report.gaps == []
    brk = pd.to_datetime(["2024-01-02 20:45", "2024-01-02 22:00"])
    _, report = validate_candles(make_df(brk), Timeframe.M15)
    assert len(report.gaps) == 1
    _, report = validate_candles(make_df(brk), Timeframe.M15, daily_breaks=[(time(21, 0), time(22, 0))])
    assert report.gaps == []


def test_weekend_gap_heuristic_does_not_hide_friday_daytime_gap():
    times = pd.to_datetime(["2024-01-05 10:00", "2024-01-07 23:00"], utc=True)
    _, report = validate_candles(make_df(times), Timeframe.M15)
    assert len(report.gaps) == 1


def test_requires_tz_aware_index():
    df = make_df(pd.date_range("2024-01-02", periods=2, freq="15min"))
    df.index = df.index.tz_localize(None)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_candles(df, Timeframe.M15)


def test_plain_csv_tz_conversion_and_roundtrip(tmp_path):
    (tmp_path / "XAUUSD_M15.csv").write_text(
        "Time,Open,High,Low,Close,Volume\n"
        "2024-01-02 03:00,2650.10,2651.00,2649.50,2650.80,10\n"
        "2024-01-02 03:15,2650.80,2652.00,2650.00,2651.50,12\n"
    )
    provider = CsvCandleProvider(tmp_path, source_tz="Etc/GMT-2")
    df = provider.get_candles(" xauusd ", Timeframe.M15)
    assert str(df.index[0]) == "2024-01-02 01:00:00+00:00"
    assert provider.last_report.ok
    assert save_candles_csv(df, tmp_path / "out" / "copy.csv").exists()


def test_mt5_export_with_points_spread(tmp_path):
    (tmp_path / "XAUUSD_M15.csv").write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2024.01.02\t03:00:00\t2650.10\t2651.00\t2649.50\t2650.80\t120\t0\t25\n"
        "2024.01.02\t03:15:00\t2650.80\t2652.00\t2650.00\t2651.50\t98\t0\t30\n"
    )
    spec = SymbolSpec(**GOLD)
    provider = CsvCandleProvider(tmp_path, spec=spec, spread_in_points=True)
    df = provider.get_candles("XAUUSD", Timeframe.M15)
    assert df["volume"].iloc[0] == 120
    assert df["spread"].iloc[0] == pytest.approx(0.25)


def test_mt5_prefers_tick_volume_and_missing_spread_stays_unknown(tmp_path):
    (tmp_path / "XAUUSD_M15.csv").write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\n"
        "2024.01.02\t03:00:00\t2650.10\t2651.00\t2649.50\t2650.80\t120\t0\n"
    )
    df = CsvCandleProvider(tmp_path).get_candles("XAUUSD", Timeframe.M15)
    assert df["volume"].iloc[0] == 120
    assert pd.isna(df["spread"].iloc[0])


def test_points_spread_requires_spec(tmp_path):
    with pytest.raises(ValueError, match="SymbolSpec"):
        CsvCandleProvider(tmp_path, spread_in_points=True)


def test_symbol_mismatch_with_spec(tmp_path):
    provider = CsvCandleProvider(tmp_path, spec=SymbolSpec(**GOLD))
    with pytest.raises(ValueError, match="Spec is for"):
        provider.get_candles("EURUSD", Timeframe.M15)


def test_dst_ambiguous_local_time_raises(tmp_path):
    (tmp_path / "XAUUSD_M15.csv").write_text(
        "time,open,high,low,close\n2024-10-27 03:30,2650,2651,2649,2650.5\n"
    )
    provider = CsvCandleProvider(tmp_path, source_tz="Europe/Athens")
    with pytest.raises(ValueError, match="Ambiguous"):
        provider.get_candles("XAUUSD", Timeframe.M15)


def test_start_end_filter_accepts_naive_and_aware_times(tmp_path):
    (tmp_path / "XAUUSD_M15.csv").write_text(
        "time,open,high,low,close\n"
        "2024-01-02 00:00,2650,2651,2649,2650.5\n"
        "2024-01-02 00:15,2650.5,2652,2650,2651\n"
        "2024-01-02 00:30,2651,2652,2650,2651.5\n"
    )
    provider = CsvCandleProvider(tmp_path)
    df = provider.get_candles(
        "XAUUSD",
        Timeframe.M15,
        start=pd.Timestamp("2024-01-02 00:15"),
        end=pd.Timestamp("2024-01-02 00:30", tz="UTC"),
    )
    assert len(df) == 1
    with pytest.raises(ValueError, match="earlier"):
        provider.get_candles(
            "XAUUSD", Timeframe.M15,
            start=pd.Timestamp("2024-01-02 00:30"),
            end=pd.Timestamp("2024-01-02 00:15"),
        )


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        CsvCandleProvider(tmp_path).get_candles("XAUUSD", Timeframe.M15)
