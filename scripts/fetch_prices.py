"""Download daily closes used by the backtest and save them to data/.

Usage: python scripts/fetch_prices.py 2025-01-01 2026-01-01
"""
import sys
from pathlib import Path

import yfinance as yf

SYMBOLS = ["PLTR", "NFLX", "PLTK"]


def main(start: str, end: str) -> None:
    closes = yf.download(SYMBOLS, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    out = Path(__file__).resolve().parent.parent / "data" / f"prices_{start[:4]}.csv"
    closes[SYMBOLS].round(4).to_csv(out)
    print(f"Saved {len(closes)} days to {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
