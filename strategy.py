from __future__ import annotations
from typing import List

from models import Signal, Trade

TREND_CONFIDENCE = 0.6
NEWS_CONFIDENCE = 0.4
TRADE_THRESHOLD = 0.5
TRADE_AMOUNT = 5_000

POSITIVE_WORDS = ("beat", "growth", "surge")
NEGATIVE_WORDS = ("miss", "lawsuit", "loss", "down")


def trend_action(closes: List[float]) -> str:
    """Momentum: compare the latest close with the first close in the window."""
    if len(closes) < 2 or closes[-1] == closes[0]:
        return "HOLD"
    return "BUY" if closes[-1] > closes[0] else "SELL"


def news_action(headlines: List[str]) -> str:
    """Keyword sentiment over headlines."""
    lowered = [h.lower() for h in headlines]
    positive = sum(any(w in h for w in POSITIVE_WORDS) for h in lowered)
    negative = sum(any(w in h for w in NEGATIVE_WORDS) for h in lowered)
    if positive > negative:
        return "BUY"
    if negative > positive:
        return "SELL"
    return "HOLD"


def _direction(action: str) -> int:
    return 1 if action == "BUY" else -1 if action == "SELL" else 0


def decide_trades(signals: List[Signal], amount: float = TRADE_AMOUNT) -> List[Trade]:
    """Confidence-weighted vote per symbol; trade when the score clears the threshold."""
    trades: List[Trade] = []
    for symbol in sorted({s.symbol for s in signals}):
        score = sum(s.confidence * _direction(s.action) for s in signals if s.symbol == symbol)
        if score >= TRADE_THRESHOLD:
            trades.append(Trade(symbol=symbol, side="BUY", amount=amount))
        elif score <= -TRADE_THRESHOLD:
            trades.append(Trade(symbol=symbol, side="SELL", amount=amount))
    return trades
