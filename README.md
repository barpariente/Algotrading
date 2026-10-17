# Algotrading

![tests](https://github.com/barpariente/Algotrading/actions/workflows/tests.yml/badge.svg)

A multi-agent paper-trading system in Python. Four CrewAI agents (trend analyst, news analyst, decision maker, risk manager) propose trades on PLTR, NFLX and PLTK. A deterministic, test-driven risk manager decides which trades go through before they reach an Alpaca paper account.

## Backtest result (2025)

The trend strategy plus the risk manager, run day by day on 2025 daily closes from $100,000:

| | Return | Max drawdown |
|---|---|---|
| Strategy | **+16.3%** | **−15.8%** |
| Equal-weight buy and hold | +35.1% | −31.5% |

491 trades executed, 243 rejected by the risk manager. The strategy captured about half of buy-and-hold's return with half its drawdown: the 30% per-stock exposure cap and 20% cash reserve limit both the upside of PLTR's rally and the losses on PLTK.

Reproduce it with `python backtest.py`. The backtest reads committed prices from `data/prices_2025.csv`, so it needs no network access or API keys. CI runs it on every push.

The backtest runs the same pure functions the agents' tasks use (`strategy.py`) and the real `RiskManagerAgent`, without calling an LLM, so the numbers are reproducible. News sentiment is left out because there is no historical headline data.

## How it works

```
 Trend Analyst ──┐
                 ├──> Decision Maker ──> Risk Manager ──> Broker
 News Analyst  ──┘    (weighted vote)    (hard limits)    (Alpaca paper / stub)
```

1. **Trend:** 5-day momentum on daily closes gives a BUY / SELL / HOLD signal (confidence 0.6).
2. **News:** keyword sentiment over headlines gives a signal (confidence 0.4).
3. **Decision:** signals are summed per symbol with their confidence; a score of ±0.5 or more proposes a $5,000 trade. A trend signal alone can trigger a trade; news alone cannot.
4. **Risk manager** (`agents.py`) approves, resizes or rejects each trade:
   - at most 5% of portfolio value per trade
   - at most 30% exposure per stock (buys are cut down to fit)
   - at least 20% of the portfolio kept in cash
   - sells limited to what is actually held
   - at most 10 trades per hour

Market data calls go through a sliding-window rate limiter (per second / hour / day) and a TTL disk cache.

## Project layout

| File | Purpose |
|---|---|
| `strategy.py` | Pure signal and decision functions shared by the agents and the backtest |
| `agents.py` | `RiskManagerAgent` and its limits (`RiskConfig`) |
| `backtest.py` | Deterministic daily backtest with a buy-and-hold benchmark |
| `crew.py`, `tasks.py`, `tools.py` | CrewAI agents, their tasks and tools |
| `agent_trader.py` | Live loop against the Alpaca paper account |
| `rate_limiter.py`, `cache.py` | Rate limiting and caching for market data |
| `alpaca_broker.py`, `alpaca_stub.py` | Alpaca paper broker and an in-memory stub for tests |
| `scripts/fetch_prices.py` | Refresh the price data used by the backtest |
| `scripts/check_alpaca_connection.py` | Check that the Alpaca keys in `.env` work |

## Running it

Requires Python 3.12 (some dependencies do not build on 3.14 yet).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q              # 26 tests, no API keys needed
python backtest.py     # 2025 backtest
```

For live paper trading, create `.env` with `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` and `OPENAI_API_KEY`, then:

```bash
python agent_trader.py realtime
```

Live mode is experimental: the agents are driven by the LLM, and the price tool does not fetch real prices yet.

## Development

The risk manager and rate limiter were built test-first. Tests cover the risk limits, the rate limiter, the strategy functions, the backtest (including a check that the 2025 result is reproducible) and the calculator tool, which only evaluates arithmetic so LLM output never reaches `eval()`.
