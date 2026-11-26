"""Environment-based configuration with conservative defaults."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("BOT_ENV", "development")
    symbol: str = os.getenv("BOT_SYMBOL", "XAUUSD").strip().upper()
    timeframe: str = os.getenv("BOT_TIMEFRAME", "M15").strip().upper()
    trading_enabled: bool = _bool_env("BOT_TRADING_ENABLED", False)
    live_trading_enabled: bool = _bool_env("BOT_LIVE_TRADING_ENABLED", False)
    log_level: str = os.getenv("BOT_LOG_LEVEL", "INFO").upper()

    def validate(self) -> None:
        if not self.symbol:
            raise ValueError("BOT_SYMBOL must not be empty.")
        if not self.timeframe:
            raise ValueError("BOT_TIMEFRAME must not be empty.")
        if self.live_trading_enabled:
            raise ValueError("Live trading is not supported by this scaffold; keep it disabled.")
        if self.trading_enabled and self.environment != "demo":
            raise ValueError("Trading can only be enabled in the demo environment.")


settings = Settings()
