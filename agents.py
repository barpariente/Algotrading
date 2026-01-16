from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from models import Portfolio, Trade, RiskDecision


@dataclass
class RiskConfig:
    max_trade_pct: float = 0.05          
    max_exposure_pct: float = 0.30       
    max_trades_per_hour: int = 10
    min_cash_pct: float = 0.20


class RiskManagerAgent:
    def __init__(self, config: RiskConfig):
        self.config = config

    def evaluate_trades(
        self,
        portfolio: Portfolio,
        trades: List[Trade],
        trade_history: List[datetime],
    ) -> List[RiskDecision]:

        now = datetime.utcnow()
        recent = [t for t in trade_history if t > now - timedelta(hours=1)]

        decisions: List[RiskDecision] = []

        for trade in trades:
            if len(recent) >= self.config.max_trades_per_hour:
                decisions.append(RiskDecision(trade.symbol, trade.side, False, 0, "Trade limit exceeded"))
                continue

            max_trade_amount = portfolio.total_value * self.config.max_trade_pct
            allowed_amount = min(trade.amount, max_trade_amount)

            # SELL: can't sell more than owned market value
            if trade.side == "SELL":
                owned_value = portfolio.holdings.get(trade.symbol, 0.0)
                allowed_amount = min(allowed_amount, owned_value)

            # BUY: can't spend more than cash
            if trade.side == "BUY":
                min_cash_required = portfolio.total_value * self.config.min_cash_pct
                if portfolio.cash - trade.amount < min_cash_required:
                    decisions.append(
                        RiskDecision(
                            symbol=trade.symbol,
                            side=trade.side,
                            approved=False,
                            final_amount=0.0,
                            reason="Cash reserve exceeded",
                        )
                    )
                    continue
                allowed_amount = min(allowed_amount, portfolio.cash)

            # exposure check (mainly for BUY)
            exposure = portfolio.holdings.get(trade.symbol, 0.0)
            max_exposure = portfolio.total_value * self.config.max_exposure_pct
            if trade.side == "BUY" and exposure + allowed_amount > max_exposure:
                allowed_amount = max(0.0, max_exposure - exposure)

            approved = allowed_amount > 0.0
            decisions.append(
                RiskDecision(
                    symbol=trade.symbol,
                    side=trade.side,
                    approved=approved,
                    final_amount=allowed_amount if approved else 0.0,
                    reason="Approved" if approved else "Rejected by risk constraints",
                )
            )

        return decisions
