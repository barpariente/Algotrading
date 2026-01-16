import os
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()

print("API KEY:", os.getenv("ALPACA_API_KEY"))
print("SECRET:", os.getenv("ALPACA_SECRET_KEY"))

client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True,
)

print(client.get_account())
