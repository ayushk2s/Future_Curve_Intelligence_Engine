"""
Step 1 — PROBE the data source.

Goal for right now: NOT to build the real pipeline. Just pull a handful of
Gold contracts + spot from Yahoo Finance and see what we actually get:
  - how far back does history go?
  - do the far-dated contracts have data, or are they empty/thin?
  - what columns come back?

Once we know that, we design the real fetcher around reality instead of guessing.

Run:  python metal_data_fetch.py
(First:  pip install yfinance pandas)
"""

import yfinance as yf
import pandas as pd

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)

# COMEX gold, active delivery months, on Yahoo: "GC" + monthcode + YY + ".CMX"
# Month codes: G=Feb J=Apr M=Jun Q=Aug V=Oct Z=Dec
# Today is Sep 2026, so these are the near-to-far live contracts:
CONTRACTS = {
    "GCV26.CMX": "Oct 2026",
    "GCZ26.CMX": "Dec 2026",
    "GCG27.CMX": "Feb 2027",
    "GCJ27.CMX": "Apr 2027",
    "GCM27.CMX": "Jun 2027",
}

# Spot proxy: front-month continuous gold. (XAUUSD=X is an alternative.)
SPOT_TICKER = "GC=F"


def probe(ticker: str, label: str) -> None:
    """Download up to 2 years of daily bars for one ticker and summarise it."""
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=False)

    if df is None or df.empty:
        print(f"  {ticker:12s} ({label:9s}) -> NO DATA")
        return

    # yfinance sometimes returns a 2-level column index for a single ticker; flatten it.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    first = df.index.min().date()
    last = df.index.max().date()
    rows = len(df)
    last_close = float(df["Close"].iloc[-1])
    last_vol = int(df["Volume"].iloc[-1]) if "Volume" in df else -1
    print(f"  {ticker:12s} ({label:9s}) -> {rows:4d} rows | {first} .. {last} "
          f"| last close {last_close:8.2f} | last vol {last_vol}")


if __name__ == "__main__":
    print("SPOT / front-month proxy:")
    probe(SPOT_TICKER, "spot")

    print("\nDATED CONTRACTS (the futures curve):")
    for tk, lbl in CONTRACTS.items():
        probe(tk, lbl)

    print("\nColumns returned for one contract (GCZ26.CMX):")
    sample = yf.download("GCZ26.CMX", period="1mo", interval="1d", progress=False, auto_adjust=False)
    if isinstance(sample.columns, pd.MultiIndex):
        sample.columns = sample.columns.get_level_values(0)
    print(list(sample.columns))
    print("\nLast 5 rows:")
    print(sample.tail())
