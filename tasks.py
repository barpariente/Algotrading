from __future__ import annotations
from crewai import Task
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
from strategy import NEWS_CONFIDENCE, TREND_CONFIDENCE, decide_trades, news_action, trend_action


_stock_client = None


def _client() -> StockHistoricalDataClient:
    # Created on first use so importing this module needs no API keys (tests, CI).
    global _stock_client
    if _stock_client is None:
        _stock_client = StockHistoricalDataClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
        )
    return _stock_client

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
    bars = _client().get_stock_bars(req).df
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

            STATE["signals"].append(Signal(symbol, trend_action(closes), TREND_CONFIDENCE))

        return STATE["signals"]

    return Task(description="Trend: momentum from recent prices", expected_output="List of trend-based buy/sell/hold signals per symbol", agent=agent, execute=run)


def news_task(agent):
    def run(_):
        for symbol in STATE["symbols"]:
            news = STATE["external_data"]["news"].get(symbol)
            if not news:
                continue

            headlines = [x.get("title", "") for x in news.get("news_results", [])]
            STATE["signals"].append(Signal(symbol, news_action(headlines), NEWS_CONFIDENCE))

        return STATE["signals"]

    return Task(description="News: heuristic sentiment from headlines", expected_output="List of news-based buy/sell/hold signals per symbol", agent=agent, execute=run)


def decision_task(agent, context_tasks):
    def run(_):
        STATE["trades"] = decide_trades(STATE["signals"])
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