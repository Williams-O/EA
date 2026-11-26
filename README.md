# EA — Forex Trading Bot

Python project for building a modular forex trading bot. Development is staged and demo-only by default. This is experimental software and does not promise profitability or constitute financial advice.

## Status
Initial scaffold only. Broker/platform and data source have not been selected. No order execution is implemented.

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

## Safety
- Trading disabled by default.
- Never put broker credentials in source or commit them.
- Research/demo only. Live mode is unsupported by this scaffold.

## Structure
- `src/forex_bot/`: application package
- `tests/`: automated tests
- `ROADMAP.md`: phases, milestones and exit criteria
