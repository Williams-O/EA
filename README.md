# EA — XAUUSD (Gold) Trading Bot

Python project for building a modular, testable trading bot focused on **XAUUSD (Gold)**. Development is staged and demo-only by default. This is experimental software; it does not promise profitability or constitute financial advice.

## Current scope
- Default instrument: `XAUUSD` (Gold vs US Dollar)
- Default research timeframe: `M15` (15-minute candles; provisional and configurable)
- Broker/platform and data source have not been selected.
- No order execution or broker connection is implemented.
- Trading remains disabled by default; live trading is unsupported.

**Broker symbol note:** some brokers name gold symbols differently (for example, `XAUUSDm`, `GOLD`, or another suffix). Set `BOT_SYMBOL` to the exact symbol your broker uses after we choose one. Do not assume symbol naming or contract specifications are identical between brokers.

## Quick start
Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
# Windows: copy .env.example .env | macOS/Linux: cp .env.example .env
python -m forex_bot
pytest
```

## Configuration
Copy `.env.example` to `.env` and edit local settings if needed. Defaults are XAUUSD and M15.

## Safety
- Trading disabled by default.
- Never put broker credentials in source or commit them.
- Research/demo only. Live mode is unsupported by this scaffold.
- Gold-specific contract size, tick value/size, volume limits, margin, trading sessions, and spread must be verified for the selected broker before any strategy/backtest or demo execution relies on them.

## Structure
- `src/forex_bot/`: application package
- `tests/`: automated tests
- `ROADMAP.md`: phases, milestones and exit criteria
