from __future__ import annotations
import json
import os
import sys
import time
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, List

from dotenv import load_dotenv
from crew import create_crew
from state import STATE
from alpaca_broker import AlpacaBroker # Ensure this handles actual Paper Trading
from models import Trade

load_dotenv()

# Logger Setup
logger = logging.getLogger("algotrading")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

SYMBOLS = ["PLTR", "NFLX", "PLTK"]

def parse_trades_from_output(crew_output: Any) -> List[Dict]:
    """
    Extracts JSON trade list from the Agent's string response.
    Handles cases where agents wrap JSON in markdown blocks.
    """
    try:
        raw_text = crew_output.raw
        # Look for JSON patterns inside the text
        match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        logger.error(f"Failed to parse agent output into trades: {e}")
        return []

def run_cycle(current_time: datetime, broker: AlpacaBroker):
    """A single iteration of the trading loop"""
    # 1. Prepare State for the Agents
    STATE["as_of"] = current_time
    STATE["symbols"] = SYMBOLS
    STATE["portfolio"] = broker.get_portfolio()
    STATE["trade_history"] = STATE.get("trade_history", [])

    logger.info(f"--- Cycle Start: {current_time} ---")
    logger.info(f"Current Portfolio: {STATE['portfolio']}")

    # 2. Run the Crew
    crew = create_crew()
    result = crew.kickoff()

    # 3. Parse and Execute
    trades_data = parse_trades_from_output(result)
    
    if not trades_data:
        logger.info("No trades approved by the Crew this cycle.")
        return

    for t_data in trades_data:
        # Convert JSON dict to our Trade model
        trade = Trade(
            symbol=t_data.get("ticker") or t_data.get("symbol"),
            side=t_data.get("action") or t_data.get("side"),
            amount=float(t_data.get("amount", 0))
        )
        
        if trade.amount > 0:
            logger.info(f"EXECUTING TRADE: {trade.side} {trade.symbol} for ${trade.amount}")
            broker.execute_trade(trade)
            STATE["trade_history"].append(current_time)

    # 4. Final log of value
    updated_portfolio = broker.get_portfolio()
    logger.info(f"Cycle Complete. New Portfolio Value: ${updated_portfolio.total_value}")

def run_realtime():
    broker = AlpacaBroker()
    logger.info("Starting REALTIME trading mode...")
    while True:
        try:
            now = datetime.now(timezone.utc)
            run_cycle(now, broker)
            logger.info("Waiting 60 seconds for next tick...")
            time.sleep(60)
        except KeyboardInterrupt:
            break

def run_backtest(date_str: str):
    broker = AlpacaBroker()
    start_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    logger.info(f"Starting BACKTEST for week starting {date_str}...")
    
    for i in range(7): # Run for 7 days
        current_day = start_date + timedelta(days=i)
        run_cycle(current_day, broker)

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent_trader.py [realtime|backtest YYYY-MM-DD]")
        return

    mode = sys.argv[1].lower()
    if mode == "realtime":
        run_realtime()
    elif mode == "backtest":
        run_backtest(sys.argv[2])

if __name__ == "__main__":
    main()