from forex_bot.config import Settings
import pytest


def test_defaults_are_safe_and_gold_focused():
    cfg = Settings()
    assert cfg.symbol == "XAUUSD"
    assert cfg.timeframe == "M15"
    assert cfg.trading_enabled is False
    assert cfg.live_trading_enabled is False


def test_symbol_and_timeframe_are_normalized():
    cfg = Settings(symbol=" xauusdm ", timeframe=" m5 ")
    assert cfg.symbol == "XAUUSDM"
    assert cfg.timeframe == "M5"


def test_empty_symbol_rejected():
    cfg = Settings(symbol=" ")
    with pytest.raises(ValueError, match="BOT_SYMBOL"):
        cfg.validate()


def test_empty_timeframe_rejected():
    cfg = Settings(timeframe="")
    with pytest.raises(ValueError, match="BOT_TIMEFRAME"):
        cfg.validate()


def test_live_mode_is_rejected():
    cfg = Settings(live_trading_enabled=True)
    with pytest.raises(ValueError, match="Live trading"):
        cfg.validate()


def test_trading_only_allowed_in_demo():
    cfg = Settings(environment="production", trading_enabled=True)
    with pytest.raises(ValueError, match="demo"):
        cfg.validate()
