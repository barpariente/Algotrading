from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from agents import Trade
import os


class AlpacaBroker:
    def __init__(self):
        self.client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=True,
        )

    def get_portfolio(self):
        account = self.client.get_account()
        positions = self.client.get_all_positions()

        holdings = {
            p.symbol: float(p.market_value)
            for p in positions
        }

        return {
            "cash": float(account.cash),
            "holdings": holdings,
            "total_value": float(account.equity),
        }

    def execute_trade(self, trade: Trade):
        order = MarketOrderRequest(
            symbol=trade.symbol,
            notional=trade.amount,
            side=OrderSide.BUY if trade.side == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )

        self.client.submit_order(order)
