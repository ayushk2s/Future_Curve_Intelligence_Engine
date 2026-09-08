"""
Step 3 — THE DATA LAYER  (blueprint section 7)

Download once, write raw CSVs to data/raw/, and never touch them again.
Everything downstream (cleaning, curve building, features) reads these files
and writes *new* files. That way a bug in the feature code can never corrupt
the source data, and a backtest can always be reproduced from the same bytes.

Tickers:
  GCV26.CMX ... GCM27.CMX  -> the 5 dated gold contracts (the curve)
  GC=F                     -> front-month continuous; the spot / near anchor
                             (see note in the plan: XAUUSD cash feed was
                              unavailable, so the front future is the anchor)

Yahoo does NOT give open interest -> that blueprint field stays empty for now.

Run:  python src/fetch_data.py          (skips files that already exist)
      python src/fetch_data.py --force  (re-download everything)
"""

import sys
import pathlib
import yfinance as yf
import pandas as pd

from _paths import RAW_DIR

TICKERS = {
    "GC=F": "front / spot anchor",
    "GCV26.CMX": "Oct 2026",
    "GCZ26.CMX": "Dec 2026",
    "GCG27.CMX": "Feb 2027",
    "GCJ27.CMX": "Apr 2027",
    "GCM27.CMX": "Jun 2027",
}

PERIOD = "2y"     # as much daily history as Yahoo reliably gives for these
INTERVAL = "1d"


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns a 2-level column index even for one ticker -> flatten."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_one(ticker: str, force: bool) -> None:
    safe_name = ticker.replace("=", "").replace(".", "_")   # "GC=F" -> "GCF"
    out = RAW_DIR / f"{safe_name}.csv"

    if out.exists() and not force:
        print(f"  skip  {ticker:12s} -> {out} already exists")
        return

    df = yf.download(ticker, period=PERIOD, interval=INTERVAL,
                     progress=False, auto_adjust=False)
    df = _flatten(df)

    if df.empty:
        print(f"  WARN  {ticker:12s} -> no data returned")
        return

    # Keep only the fields the blueprint's data model uses; drop 'Adj Close'
    # (futures have no splits/dividends, so it just duplicates 'Close').
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[cols].copy()
    df.index.name = "date"

    out.write_text(df.to_csv())
    print(f"  ok    {ticker:12s} -> {out}  ({len(df)} rows, "
          f"{df.index.min().date()} .. {df.index.max().date()})")


def main() -> None:
    force = "--force" in sys.argv
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"writing raw data to {RAW_DIR.resolve()}\n")
    for ticker, label in TICKERS.items():
        print(f"[{label}]")
        fetch_one(ticker, force)
    print("\ndone. raw files are immutable -- downstream steps must not edit them.")


if __name__ == "__main__":
    main()
