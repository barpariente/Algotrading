"""Manual check that the Alpaca paper-trading keys in .env work.

Usage: python scripts/check_alpaca_connection.py
"""
import os

from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()

client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True,
)

account = client.get_account()
print(f"Connected. Account status: {account.status}, cash: {account.cash}")
