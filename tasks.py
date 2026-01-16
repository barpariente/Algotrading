from __future__ import annotations
from crewai import Task
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from state import STATE
from models import Signal, Trade, RateLimitConfig
from agents import RiskManagerAgent, RiskConfig
from cache import DiskCache
from rate_limiter import RateLimiter
from tools import RiskValidationTool


_stock_client = StockHistoricalDataClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
)

_price_cache = DiskCache(".cache")
_price_limiter = RateLimiter(RateLimitConfig(per_second=1, per_hour=60, per_day=600))


def _fetch_recent_closes(symbol: str, as_of: datetime, days: int = 5) -> list[float]:
    start = (as_of - timedelta(days=days + 3)).replace(tzinfo=timezone.utc)
    end = as_of.replace(tzinfo=timezone.utc)

    key = f"alpaca_closes:{symbol}:{start.date()}:{end.date()}:D"
    cached = _price_cache.get(key)
    if cached is not None:
        return cached

    if not _price_limiter.allow("alpaca_prices", datetime.utcnow()):
        raise RuntimeError("Rate limit exceeded for Alpaca market data")

    req = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    bars = _stock_client.get_stock_bars(req).df
    if bars.empty:
        closes = []
    else:
        closes = bars["close"].tolist()

    _price_cache.set(key, closes, ttl_seconds=60 * 60)  # 1h
    return closes


def trend_task(agent):
    def run(_):
        as_of = STATE["as_of"]
        for symbol in STATE["symbols"]:
            closes = _fetch_recent_closes(symbol, as_of, days=5)
            if len(closes) < 2:
                continue

            if closes[-1] > closes[0]:
                action = "BUY"
            elif closes[-1] < closes[0]:
                action = "SELL"
            else:
                action = "HOLD"

            STATE["signals"].append(Signal(symbol=symbol, action=action, confidence=0.6))

        return STATE["signals"]

    return Task(description="Trend: momentum from recent prices", expected_output="List of trend-based buy/sell/hold signals per symbol", agent=agent, execute=run)


def news_task(agent):
    def run(_):
        for symbol in STATE["symbols"]:
            news = STATE["external_data"]["news"].get(symbol)
            if not news:
                continue

            headlines = [x.get("title", "").lower() for x in news.get("news_results", [])]
            positive = sum(("beat" in h or "growth" in h or "surge" in h) for h in headlines)
            negative = sum(("miss" in h or "lawsuit" in h or "loss" in h or "down" in h) for h in headlines)

            if positive > negative:
                action = "BUY"
            elif negative > positive:
                action = "SELL"
            else:
                action = "HOLD"

            STATE["signals"].append(Signal(symbol=symbol, action=action, confidence=0.4))

        return STATE["signals"]

    return Task(description="News: heuristic sentiment from headlines", expected_output="List of news-based buy/sell/hold signals per symbol", agent=agent, execute=run)


def decision_task(agent, context_tasks):
    def run(_):
        votes = defaultdict(int)
        for s in STATE["signals"]:
            votes[s.symbol] += (1 if s.action == "BUY" else -1 if s.action == "SELL" else 0)

        STATE["trades"] = []

        for symbol in {s.symbol for s in STATE["signals"]}:
            score = sum(
                s.confidence * (
                    1 if s.action == "BUY"
                    else -1 if s.action == "SELL"
                    else 0
                )
                for s in STATE["signals"]
                if s.symbol == symbol
            )

            if score >= 0.5:
                STATE["trades"].append(
                    Trade(symbol=symbol, side="BUY", amount=5_000)
                )
            elif score <= -0.5:
                STATE["trades"].append(
                    Trade(symbol=symbol, side="SELL", amount=5_000)
                )

        return STATE["trades"]

    return Task(
        description="""Review the price trends from the Trend Analyst AND news sentiment 
        from the News Analyst. You MUST decide to BUY or SELL if there is a clear trend. 
        Do not default to HOLD if data is available.""",
        expected_output="A JSON list of trades: [{'ticker': 'PLTR', 'action': 'BUY', 'amount': 5000}]",
        agent=agent,
        context=context_tasks
    )


def risk_task(agent):
    def run(_):
        risk = RiskManagerAgent(RiskConfig())
        decisions = risk.evaluate_trades(
            portfolio=STATE["portfolio"],
            trades=STATE["trades"],
            trade_history=STATE["trade_history"],
        )
        STATE["decisions"] = decisions
        STATE["trades_to_execute"] = [
            Trade(d.symbol, d.side, d.final_amount) for d in decisions if d.approved
        ]
        return decisions

    return Task(
        description="Verify trades using risk_validator. Output ONLY a final JSON list of approved trades.",
        expected_output="A JSON list of trades: [{'ticker': 'SYMBOL', 'action': 'BUY/SELL', 'amount': 123}]",
        agent=agent,
        tools=[RiskValidationTool()]
    )