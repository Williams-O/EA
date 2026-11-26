from forex_bot.config import Settings
import pytest

def test_defaults_are_safe():
    cfg = Settings()
    assert cfg.trading_enabled is False
    assert cfg.live_trading_enabled is False

def test_live_mode_is_rejected():
    cfg = Settings(live_trading_enabled=True)
    with pytest.raises(ValueError, match="Live trading"):
        cfg.validate()

def test_trading_only_allowed_in_demo():
    cfg = Settings(environment="production", trading_enabled=True)
    with pytest.raises(ValueError, match="demo"):
        cfg.validate()
