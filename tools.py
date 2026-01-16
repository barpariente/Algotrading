import os
import time
from functools import wraps
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from diskcache import Cache
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from agents import RiskManagerAgent, RiskConfig
from models import Trade
from state import STATE

# 1. Caching & Rate Limiter Logic
cache = Cache(".trading_cache")

def rate_limit(calls_per_minute):
    interval = 60.0 / calls_per_minute
    def decorator(func):
        last_called = [0.0]
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < interval:
                time.sleep(interval - elapsed)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

# 2. Custom Calculator Tool (Requirement: At least 1 custom tool)
class TradeCalculatorTool(BaseTool):
    name: str = "trade_calculator"
    description: str = "Perform financial math. Useful for calculating shares based on price."

    def _run(self, expression: str) -> str:
        # Simple/Safe math evaluation
        try: return str(eval(expression))
        except: return "Error in calculation"

# 3. Alpaca Price Tool (Requirement: Use Stubs/Mocks during dev)
class StockPriceTool(BaseTool):
    name: str = "stock_price_fetcher"
    description: str = "Fetches the last 5 days of closing prices for a symbol."

    @rate_limit(calls_per_minute=20)
    def _run(self, symbol: str) -> str:
        # TDD Hint: You should check if we are in 'DEV' mode to return mock data
        if os.getenv("ENV") == "DEV":
            return "150.0, 152.0, 149.0, 155.0, 158.0" # Mocked data
        
        # Real logic for Paper Trading
        client = StockHistoricalDataClient(os.getenv("APCA_API_KEY"), os.getenv("APCA_API_SECRET"))
        # ... logic to fetch from Alpaca and cache result ...
        return "prices_here"

# Define the "Schema" so the LLM knows exactly what inputs to provide
class RiskCheckInput(BaseModel):
    symbol: str = Field(..., description="The stock symbol (PLTR, NFLX, or PLTK).")
    side: str = Field(..., description="Whether to 'BUY' or 'SELL'.")
    amount: float = Field(..., description="The dollar amount of the proposed trade.")

class RiskValidationTool(BaseTool):
    name: str = "risk_validator"
    description: str = (
        "Validates a proposed trade against portfolio limits, "
        "including 30% max exposure per stock and 20% cash reserve."
    )
    args_schema: Type[BaseModel] = RiskCheckInput

    def _run(self, symbol: str, side: str, amount: float) -> str:
        """
        This method executes when the Agent decides to check risk.
        It uses your custom Python logic.
        """
        # 1. Initialize your custom logic class
        # You can pass a custom RiskConfig here if you want to change limits
        risk_engine = RiskManagerAgent(RiskConfig())

        # 2. Create a Trade object from the Agent's input
        proposed_trade = Trade(
            symbol=symbol.upper(),
            side=side.upper(),
            amount=amount
        )

        # 3. Call your TDD-tested evaluation logic
        # We pull current portfolio and history from your global STATE
        decisions = risk_engine.evaluate_trades(
            portfolio=STATE["portfolio"],
            trades=[proposed_trade],
            trade_history=STATE["trade_history"]
        )

        # 4. Format the result for the Agent to read
        decision = decisions[0]
        
        if decision.approved:
            return (
                f"VERDICT: APPROVED. "
                f"You can proceed with {decision.side} {decision.symbol} for ${decision.final_amount}. "
                f"Reasoning: {decision.reason}"
            )
        else:
            return (
                f"VERDICT: REJECTED. "
                f"The trade for {symbol} was denied. "
                f"Reasoning: {decision.reason}. "
                f"Suggest a smaller amount or a different stock."
            )