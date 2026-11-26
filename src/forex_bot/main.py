"""CLI entry point. No broker connection or order placement occurs."""
import logging
from .config import settings

def main() -> None:
    settings.validate()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("forex_bot")
    log.info("Scaffold started (environment=%s).", settings.environment)
    log.info("Trading enabled: %s", settings.trading_enabled)
    log.info("No broker connection or orders are implemented.")

if __name__ == "__main__":
    main()
