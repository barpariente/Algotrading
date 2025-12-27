# agents.py
from dataclasses import dataclass
from typing import Dict, List, Literal
from datetime import datetime, timedelta

from models import Portfolio, Trade, RiskDecision, Signal, RiskConfig
from cache import SimpleCache

news_cache = SimpleCache(ttl_seconds=60 * 60)
from data_providers import fetch_market_price
from agents import Signal


def trend_agent(symbols):
    signals = []
    for symbol in symbols:
        price = fetch_market_price(symbol)

        if price > 100:
            signals.append(
                Signal(symbol, action="BUY", confidence=0.6)
            )
        else:
            signals.append(
                Signal(symbol, action="SELL", confidence=0.6)
            )

    return signals

# ---------- Risk Manager (TDD) ----------

class RiskManagerAgent:
    def __init__(
        self,
        config: RiskConfig,
    ):
        self.config = config

    def evaluate_trades(
        self,
        portfolio: Portfolio,
        trades: list[Trade],
        trade_history: list[datetime],
    ) -> List[RiskDecision]:

        now = datetime.utcnow()
        recent_trades = [t for t in trade_history if t > now - timedelta(hours=1)]

        decisions = []

        for trade in trades:
            if trade.side == "SELL":
                owned_amount = portfolio.holdings.get(trade.symbol, 0)

                if owned_amount <= 0:
                    decisions.append(
                        RiskDecision(
                            trade.symbol,
                            trade.side,
                            False,
                            0,
                            "No holdings to sell",
                        )
                    )
                    continue

                final_amount = min(trade.amount, owned_amount)

                decisions.append(
                    RiskDecision(
                        trade.symbol,
                        trade.side,
                        True,
                        final_amount,
                        "Approved",
                    )
                )
                continue

            if len(recent_trades) >= self.config.max_trades_per_hour:
                decisions.append(
                    RiskDecision(
                        trade.symbol, trade.side, False, 0, "Trade limit exceeded"
                    )
                )
                continue

            max_trade_amount = portfolio.total_value * self.config.max_trade_pct
            allowed_amount = min(trade.amount, max_trade_amount)

            exposure = portfolio.holdings.get(trade.symbol, 0)
            max_exposure = portfolio.total_value * self.config.max_exposure_pct
            allowed_amount = min(allowed_amount, max_exposure - exposure)

            if portfolio.cash - allowed_amount < portfolio.total_value * self.config.min_cash_pct:
                decisions.append(
                    RiskDecision(
                        trade.symbol, trade.side, False, 0, "Cash reserve violated"
                    )
                )
                continue

            decisions.append(
                RiskDecision(
                    trade.symbol, trade.side, True, allowed_amount, "Approved"
                )
            )

        return decisions


# ---------- Decision Coordinator ----------

class DecisionCoordinatorAgent:
    def decide(self, signals: List[Signal], portfolio: Portfolio) -> List[Trade]:
        score = {}
        for s in signals:
            score.setdefault(s.symbol, 0)
            score[s.symbol] += (
                s.confidence if s.action == "BUY"
                else -s.confidence if s.action == "SELL"
                else 0
            )

        trades = []
        for symbol, s in score.items():
            if s >= 0.5:
                trades.append(
                    Trade(symbol, "BUY", portfolio.total_value * 0.05)
                )
            elif s <= -0.5:
                trades.append(
                    Trade(symbol, "SELL", portfolio.total_value * 0.05)
                )

        return trades


# ---------- Trend & News (simple stubs for now) ----------

def trend_signals():
    return [
        Signal("PLTR", "HOLD", 0.5),
        Signal("NFLX", "HOLD", 0.5),
        Signal("PLTK", "HOLD", 0.5),
    ]


def news_signals():
    return [
        Signal("PLTR", "HOLD", 0.4),
        Signal("NFLX", "HOLD", 0.4),
        Signal("PLTK", "HOLD", 0.4),
    ]
