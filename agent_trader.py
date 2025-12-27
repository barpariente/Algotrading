from __future__ import annotations

import json
import os
import sys
import time
import hashlib
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, List

import requests

from crew import create_crew
from state import STATE
from alpaca_stub import AlpacaStub  # Replace with real Alpaca wrapper if you have one
from rate_limiter import RateLimiter
from models import RateLimitConfig, Portfolio, Trade, RiskDecision

from dotenv import load_dotenv
load_dotenv()

from alpaca_broker import AlpacaBroker

broker = AlpacaBroker()

portfolio = broker.get_portfolio()
STATE["portfolio"] = portfolio

for trade in STATE["trades_to_execute"]:
    broker.execute_trade(trade)
# ----------------------------
# Logging
# ----------------------------
logger = logging.getLogger("algotrading")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(_handler)


# ----------------------------
# Disk cache (simple & good for assignment)
# ----------------------------
class DiskCache:
    """
    Very simple persistent cache.
    - Key: string
    - Value: JSON-serializable object
    - TTL optional (seconds). If ttl_seconds=None, cache never expires.
    """
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path_for_key(self, key: str) -> str:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._path_for_key(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            expires_at = payload.get("expires_at")
            if expires_at is not None:
                exp = datetime.fromisoformat(expires_at)
                if datetime.now(timezone.utc) > exp:
                    # expired
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    return None
            return payload["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        path = self._path_for_key(key)
        payload: Dict[str, Any] = {"value": value, "expires_at": None}
        if ttl_seconds is not None:
            payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


# ----------------------------
# Paid/slow API wrappers + fairness
# ----------------------------
disk_cache = DiskCache(".cache")

# Rate limit for external paid services (SerpAPI etc.)
paid_api_limiter = RateLimiter(
    RateLimitConfig(per_second=1, per_hour=30, per_day=200)
)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

def _cache_key(prefix: str, params: Dict[str, Any]) -> str:
    s = prefix + ":" + json.dumps(params, sort_keys=True, ensure_ascii=False)
    return s


def serpapi_google_news(
    query: str,
    start_date: datetime,
    end_date: datetime,
    *,
    ttl_seconds: int = 60 * 60 * 24,
) -> Dict[str, Any]:
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY is missing. Set it in your environment.")

    params = {
        "engine": "google_news",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "hl": "en",
        "gl": "us",
    }

    key = _cache_key("serpapi_news", {"query": query, "start": start_date.date().isoformat(), "end": end_date.date().isoformat()})
    cached = disk_cache.get(key)
    if cached is not None:
        logger.info(f"[cache hit] SerpAPI news: {query} {start_date.date()}..{end_date.date()}")
        return cached

    # Rate limit
    now = datetime.utcnow()
    if not paid_api_limiter.allow("serpapi_news", now):
        raise RuntimeError("Rate limit exceeded for SerpAPI news")

    # IMPORTANT: fairness — enforce date in query (Google News doesn't always accept clean parameters)
    # We'll append a simple range hint. This is not perfect, but it's an honest attempt for the assignment.
    # For strict fairness, use sources that support explicit date filters.
    date_hint = f" after:{start_date.date().isoformat()} before:{end_date.date().isoformat()}"
    params["q"] = query + date_hint

    logger.info(f"[api call] SerpAPI news: {query} {start_date.date()}..{end_date.date()}")
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    disk_cache.set(key, data, ttl_seconds=ttl_seconds)
    return data


def serpapi_google_trends(
    query: str,
    start_date: datetime,
    end_date: datetime,
    *,
    ttl_seconds: int = 60 * 60 * 24,
) -> Dict[str, Any]:
    """
    SerpAPI Google Trends engine (if you choose to use it).
    Cached by (query,start,end).
    """
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY is missing. Set it in your environment.")

    params = {
        "engine": "google_trends",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "hl": "en",
        "geo": "US",
    }

    key = _cache_key("serpapi_trends", {"query": query, "start": start_date.date().isoformat(), "end": end_date.date().isoformat()})
    cached = disk_cache.get(key)
    if cached is not None:
        logger.info(f"[cache hit] SerpAPI trends: {query} {start_date.date()}..{end_date.date()}")
        return cached

    now = datetime.utcnow()
    if not paid_api_limiter.allow("serpapi_trends", now):
        raise RuntimeError("Rate limit exceeded for SerpAPI trends")

    logger.info(f"[api call] SerpAPI trends: {query} {start_date.date()}..{end_date.date()}")
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    disk_cache.set(key, data, ttl_seconds=ttl_seconds)
    return data


# ----------------------------
# Portfolio / Broker (paper trading)
# ----------------------------
def get_broker() -> AlpacaStub:
    """
    For the assignment: you can keep AlpacaStub, or replace with a real Alpaca paper broker wrapper.
    """
    return AlpacaStub(cash=100_000)


def read_portfolio(broker: AlpacaStub) -> Portfolio:
    return broker.get_portfolio()


def execute_trades(broker: AlpacaStub, trades: List[Trade]) -> None:
    for t in trades:
        broker.submit_trade(t.symbol, t.side, t.amount)


# ----------------------------
# Time windows & fairness helpers
# ----------------------------
def week_window(start_date_utc: datetime) -> Tuple[datetime, datetime]:
    """
    Returns [start, end) for one week.
    """
    start = start_date_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end


def fair_news_window_for_prediction(prediction_start: datetime) -> Tuple[datetime, datetime]:
    """
    Fairness rule: if you predict starting at time T,
    don't use news from after T (or too close if you want stricter).
    We'll use: end = T - 1 day.
    """
    end = (prediction_start - timedelta(days=1)).replace(tzinfo=timezone.utc)
    start = end - timedelta(days=7)
    return start, end


# ----------------------------
# MAIN LOOPS
# ----------------------------
SYMBOLS = ["PLTR", "NFLX", "PLTK"]


def run_backtest_one_week(week_start_date: str) -> None:
    """
    week_start_date format: YYYY-MM-DD (UTC)
    """
    broker = get_broker()

    start = datetime.fromisoformat(week_start_date).replace(tzinfo=timezone.utc)
    w_start, w_end = week_window(start)

    logger.info(f"Backtest week: {w_start.date()} .. {w_end.date()} (UTC)")

    # For backtest, we step through the week in daily steps (simple).
    current = w_start
    while current < w_end:
        step_end = current + timedelta(days=1)

        # Fairness: only use news that ends BEFORE the day you're "predicting"
        news_start, news_end = fair_news_window_for_prediction(current)

        # Put run context into STATE so tasks can use it
        STATE["run_mode"] = "backtest"
        STATE["as_of"] = current
        STATE["market_window"] = (current, step_end)
        STATE["news_window"] = (news_start, news_end)
        STATE["symbols"] = SYMBOLS

        # Pull portfolio now (paper)
        portfolio = read_portfolio(broker)
        STATE["portfolio"] = portfolio
        STATE["trade_history"] = STATE.get("trade_history", [])

        logger.info(f"--- Backtest step as_of={current.isoformat()} ---")
        logger.info(f"Portfolio before: {portfolio}")

        # Optional: call SerpAPI once per symbol per step (cached)
        # Store into STATE so your News task can use it without calling again
        STATE["external_data"] = {"news": {}, "trends": {}}
        try:
            for sym in SYMBOLS:
                q = f"{sym} stock"
                news_data = serpapi_google_news(q, news_start, news_end)
                STATE["external_data"]["news"][sym] = news_data

                trends_data = serpapi_google_trends(q, news_start, news_end)
                STATE["external_data"]["trends"][sym] = trends_data
        except Exception as e:
            logger.warning(f"External data fetch failed (continuing with what we have): {e}")

        crew = create_crew()
        crew.kickoff()

        # Expect your tasks to populate:
        # STATE["approved_trades"] (list[Trade]) or STATE["trades_to_execute"]
        trades_to_execute: List[Trade] = STATE.get("trades_to_execute", []) or STATE.get("approved_trades", [])
        if trades_to_execute:
            logger.info(f"Executing {len(trades_to_execute)} trades (paper) for this step...")
            execute_trades(broker, trades_to_execute)
            STATE["trade_history"].append(datetime.utcnow().replace(tzinfo=timezone.utc))

        portfolio_after = read_portfolio(broker)
        logger.info(f"Portfolio after: {portfolio_after}")

        current = step_end

    final_portfolio = read_portfolio(broker)
    logger.info(f"Backtest completed. Final portfolio: {final_portfolio}")


def run_realtime_loop(poll_seconds: int = 30) -> None:
    """
    Realtime-ish loop. Stops when user presses Ctrl+C.
    Uses fairness windows: news is always up to "now - 1 day" (strict).
    """
    broker = get_broker()
    logger.info("Starting algo-trading bot (paper trading) in realtime loop...")
    logger.info("Press Ctrl+C to exit.")

    try:
        while True:
            now = datetime.now(timezone.utc)

            # Fairness: don't include news from after now; we use now-1day cutoff
            news_start, news_end = fair_news_window_for_prediction(now)

            STATE["run_mode"] = "realtime"
            STATE["as_of"] = now
            STATE["market_window"] = (now - timedelta(minutes=5), now)
            STATE["news_window"] = (news_start, news_end)
            STATE["symbols"] = SYMBOLS

            portfolio = read_portfolio(broker)
            STATE["portfolio"] = portfolio
            STATE["trade_history"] = STATE.get("trade_history", [])

            logger.info("\n--- New trading cycle ---")
            logger.info(f"Current portfolio: {portfolio}")

            # Fetch external (paid) data once per cycle (cached & rate-limited)
            STATE["external_data"] = {"news": {}, "trends": {}}
            try:
                for sym in SYMBOLS:
                    q = f"{sym} stock"
                    STATE["external_data"]["news"][sym] = serpapi_google_news(q, news_start, news_end)
                    STATE["external_data"]["trends"][sym] = serpapi_google_trends(q, news_start, news_end)
            except Exception as e:
                logger.warning(f"External data fetch failed (continuing with what we have): {e}")

            crew = create_crew()
            crew.kickoff()

            trades_to_execute: List[Trade] = STATE.get("trades_to_execute", []) or STATE.get("approved_trades", [])
            if trades_to_execute:
                logger.info(f"Executing {len(trades_to_execute)} trades (paper)...")
                for t in trades_to_execute:
                    logger.info(f"TRADE: {t}")
                execute_trades(broker, trades_to_execute)
                STATE["trade_history"].append(now)

            portfolio_after = read_portfolio(broker)
            logger.info(f"Portfolio now: {portfolio_after}")

            time.sleep(poll_seconds)

    except KeyboardInterrupt:
        logger.info("Exiting on user request.")


def main():
    """
    Usage:
      python agent_trader.py realtime
      python agent_trader.py backtest 2025-01-06
    """
    if len(sys.argv) < 2:
        print("Usage:\n  python agent_trader.py realtime\n  python agent_trader.py backtest YYYY-MM-DD")
        sys.exit(1)

    mode = sys.argv[1].lower().strip()

    if mode == "realtime":
        run_realtime_loop(poll_seconds=30)
        return

    if mode == "backtest":
        if len(sys.argv) < 3:
            print("Usage: python agent_trader.py backtest YYYY-MM-DD")
            sys.exit(1)
        run_backtest_one_week(sys.argv[2])
        return

    print("Unknown mode. Use: realtime | backtest")
    sys.exit(1)


if __name__ == "__main__":
    main()
