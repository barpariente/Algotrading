"""Deterministic backtest of the trend strategy and the risk manager on daily closes.

The LLM agents are not called here: each simulated day runs the same pure
functions the crew's tasks use (strategy.py) and the RiskManagerAgent, so the
result is reproducible. News sentiment is skipped because there is no
historical headline data.

Usage: python backtest.py [data/prices_2025.csv]
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from typing import Dict, List

from agents import RiskConfig, RiskManagerAgent
from models import Portfolio, Signal
from strategy import TREND_CONFIDENCE, decide_trades, trend_action

STARTING_CASH = 100_000.0
LOOKBACK_DAYS = 5


@dataclass
class BacktestResult:
    final_value: float
    total_return: float
    max_drawdown: float
    benchmark_return: float
    benchmark_max_drawdown: float
    trades_executed: int
    trades_rejected: int


def load_prices(path: str) -> tuple[List[str], Dict[str, List[float]]]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    symbols = [k for k in rows[0] if k != "Date"]
    dates = [r["Date"] for r in rows]
    return dates, {s: [float(r[s]) for r in rows] for s in symbols}


def max_drawdown(values: List[float]) -> float:
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def run_backtest(prices: Dict[str, List[float]], config: RiskConfig | None = None) -> BacktestResult:
    risk = RiskManagerAgent(config or RiskConfig())
    symbols = list(prices)
    days = len(next(iter(prices.values())))

    cash = STARTING_CASH
    shares = {s: 0.0 for s in symbols}
    equity: List[float] = []
    executed = rejected = 0

    for day in range(days):
        price = {s: prices[s][day] for s in symbols}
        holdings = {s: shares[s] * price[s] for s in symbols}
        total = cash + sum(holdings.values())
        equity.append(total)

        if day < LOOKBACK_DAYS - 1:
            continue

        signals = [
            Signal(s, trend_action(prices[s][day - LOOKBACK_DAYS + 1 : day + 1]), TREND_CONFIDENCE)
            for s in symbols
        ]
        trades = decide_trades(signals)
        portfolio = Portfolio(cash=cash, holdings=holdings, total_value=total)

        for d in risk.evaluate_trades(portfolio, trades, trade_history=[]):
            if not d.approved:
                rejected += 1
                continue
            executed += 1
            qty = d.final_amount / price[d.symbol]
            if d.side == "BUY":
                cash -= d.final_amount
                shares[d.symbol] += qty
            else:
                cash += d.final_amount
                shares[d.symbol] = max(0.0, shares[d.symbol] - qty)

    per_symbol = STARTING_CASH / len(symbols)
    benchmark = [
        sum(per_symbol * prices[s][day] / prices[s][0] for s in symbols) for day in range(days)
    ]

    return BacktestResult(
        final_value=equity[-1],
        total_return=equity[-1] / STARTING_CASH - 1,
        max_drawdown=max_drawdown(equity),
        benchmark_return=benchmark[-1] / STARTING_CASH - 1,
        benchmark_max_drawdown=max_drawdown(benchmark),
        trades_executed=executed,
        trades_rejected=rejected,
    )


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/prices_2025.csv"
    dates, prices = load_prices(path)
    r = run_backtest(prices)
    print(f"Backtest {dates[0]} to {dates[-1]} on {', '.join(prices)}")
    print(f"  Strategy:     {r.total_return:+.1%} return, {r.max_drawdown:.1%} max drawdown, final ${r.final_value:,.0f}")
    print(f"  Buy and hold: {r.benchmark_return:+.1%} return, {r.benchmark_max_drawdown:.1%} max drawdown (equal weight)")
    print(f"  Trades: {r.trades_executed} executed, {r.trades_rejected} rejected by the risk manager")


if __name__ == "__main__":
    main()
