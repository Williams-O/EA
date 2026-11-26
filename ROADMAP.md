# Forex Bot Development Roadmap

## Goal
Develop a modular, testable forex trading system in Python. The first release is demo-only; live trading is out of scope until strategy validation, safety controls, and broker integration are reviewed.

## Principles
- Risk controls override strategy signals.
- No strategy is assumed profitable; validate with realistic costs and out-of-sample data.
- Separate data, strategy, risk, execution, and monitoring modules.
- Never commit credentials or secrets.
- Avoid Martingale, grid averaging, and uncontrolled position sizing.

## Phase 0 — Foundation (current)
- [x] Document scope and roadmap
- [x] Establish Python packaging and scaffold
- [x] Environment-based config with safe defaults
- [x] Logging and basic tests
- [ ] Choose broker/platform and data source (MT5, broker API, etc.)
- [ ] Confirm instruments, timezone, and sessions

Exit: install/test succeeds, app starts in safe mode, no secrets in repo.

## Phase 1 — Market data
- [ ] Provider interface and candle model
- [ ] OHLCV retrieval, symbol specs, spread and timestamps
- [ ] Validate missing/duplicate/out-of-order candles and invalid values
- [ ] Normalize timezones and persist local data
- [ ] Data-quality tests and fixtures

Exit: repeatable, validated history and demo feed.

## Phase 2 — Strategy prototype
- [ ] Strategy interface returns BUY, SELL, or NO_TRADE
- [ ] Prototype EMA 20/50 crossover, EMA 200 trend filter, RSI 14 confirmation
- [ ] Evaluate only closed candles; avoid look-ahead bias
- [ ] Configurable parameters and deterministic tests

Research hypothesis (not a recommendation): long when EMA20 crosses above EMA50, price is above EMA200 and RSI(14) is above 50 but below an upper threshold; short conditions mirrored. Skip incomplete data or trades rejected by risk/spread filters.

Exit: documented assumptions and passing signal tests.

## Phase 3 — Backtesting
- [ ] Event-driven backtest or vetted framework
- [ ] Include spread, commissions, swaps, slippage and realistic fills
- [ ] Prevent look-ahead bias and data leakage
- [ ] Development/validation/out-of-sample splits
- [ ] Walk-forward and parameter-sensitivity analysis
- [ ] Report net return, max drawdown, profit factor, expectancy, Sharpe, trade count, streaks

Exit: reproducible cost-inclusive results across market regimes. Past performance is not predictive.

## Phase 4 — Risk management
- [ ] Position sizing from stop distance and equity
- [ ] Demo default risk per trade: 0.5% (configurable)
- [ ] Demo default daily loss cap: 2% (configurable)
- [ ] Max exposure and concurrent positions
- [ ] Mandatory protective stop; reject orders without valid stop
- [ ] Spread, volatility, stale-data and session filters
- [ ] Cooldown and stop-after-loss controls
- [ ] Emergency kill switch; fail closed on invalid config

Exit: tests prove limits cannot be bypassed by strategy signals.

## Phase 5 — Demo execution
- [ ] Select broker/platform; adapter behind execution interface
- [ ] Verify volume steps, contract/pip values, margin, stop rules, order semantics
- [ ] Idempotency, retry limits, order reconciliation and disconnect safety
- [ ] Demo forward test; audit signal, decision, order, fill and exit
- [ ] Avoid blind retries where order acceptance is uncertain

Exit: sustained demo operation with reconciled orders and no safety failures.

## Phase 6 — Monitoring and operations
- [ ] Structured logs and audit trail
- [ ] Dashboard: state, data health, signals, positions, equity, drawdown, limits
- [ ] Alerts for disconnects, errors, limit triggers and kill switch
- [ ] Restart/recovery and graceful shutdown
- [ ] Deployment, backup and incident runbook

## Phase 7 — Live-readiness review (not authorization)
- [ ] Independent code, strategy and risk review
- [ ] Robust out-of-sample and walk-forward results
- [ ] Extended demo forward test with documented results
- [ ] Verify regulations, broker terms and security requirements
- [ ] Explicit human approval of live mode and settings
- [ ] Live mode disabled by default; requires deliberate separate configuration

## Initial research setup (provisional)
- Pair: EUR/USD; timeframe: 15-minute
- EMA 20/50 crossover + EMA 200 filter + RSI 14
- ATR-based stop; configurable risk/reward target
- Demo risk cap: 0.5% per trade; daily loss cap: 2%
- Local development; demo account only

## v1 definition of done
Demo-only bot retrieves validated market data, generates reproducible signals, backtests with costs, sizes positions safely, executes and reconciles demo orders, halts on risk/data/connectivity faults, and produces auditable reports.