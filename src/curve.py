"""
Step 4 — CLEANING + CURVE CONSTRUCTION  (blueprint section 9)

Reads the immutable raw CSVs, removes non-trading junk rows, and assembles:

  data/clean/panel_prices.csv  -- wide: one row per date, one column per contract
  data/clean/curve_long.csv    -- tidy: one row per (date, contract) with the
                                  normalized fields  = blueprint section 26 record

The "futures curve" for a given date is simply: take that date's row, attach
each contract's T (years to expiry, computed as of that date), sort by T.
That sorted (T, price) sequence IS the curve.

Run:  python src/curve.py
"""

import pathlib
import pandas as pd
from contracts import parse_comex_gold

from _paths import RAW_DIR as RAW, CLEAN_DIR as CLEAN


# raw filename -> exchange symbol
DATED = {
    "GCV26_CMX.csv": "GCV26.CMX",
    "GCZ26_CMX.csv": "GCZ26.CMX",
    "GCG27_CMX.csv": "GCG27.CMX",
    "GCJ27_CMX.csv": "GCJ27.CMX",
    "GCM27_CMX.csv": "GCM27.CMX",
}
FRONT_FILE = "GCF.csv"      # GC=F front-month continuous -> spot / near anchor


def load_clean(fname: str) -> tuple[pd.DataFrame, int]:
    """
    Load one raw CSV and drop non-trading rows.

    Rule: Volume <= 0 means nothing actually traded that day -- these are
    Yahoo backfill placeholders (OHLC all equal, volume 0). Drop them
    rather than invent prices. This is the ONLY cleaning rule for the MVP;
    it is deliberately conservative so real thin days are not deleted.
    """
    df = (pd.read_csv(RAW / fname, parse_dates=["date"])
            .set_index("date")
            .sort_index())
    keep = df["Volume"] > 0
    removed = int((~keep).sum())
    return df.loc[keep], removed


def build() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)

    close, vol = {}, {}
    print("cleaning:")
    for fname, sym in DATED.items():
        df, removed = load_clean(fname)
        print(f"  {sym:12s} kept {len(df):4d}  (dropped {removed} zero-volume rows)")
        close[sym] = df["Close"]
        vol[sym] = df["Volume"]

    prices = pd.DataFrame(close).sort_index()
    volumes = pd.DataFrame(vol).sort_index().reindex(prices.index)

    front, _ = load_clean(FRONT_FILE)
    prices.insert(0, "FRONT", front["Close"].reindex(prices.index))

    dated_syms = list(DATED.values())
    full = prices.dropna(subset=dated_syms)          # keep dates where all 5 exist
    print(f"\npanel: {len(full)} dates with all 5 contracts, "
          f"{full.index.min().date()} .. {full.index.max().date()}")

    prices.to_csv(CLEAN / "panel_prices.csv")

    # ---- tidy long form: the blueprint's normalized record (section 26) ----
    meta = {sym: parse_comex_gold(sym) for sym in dated_syms}
    rows = []
    for d, r in full.iterrows():
        as_of = d.date()
        for sym in dated_syms:
            c = meta[sym]
            rows.append({
                "date": d,
                "underlying": c.underlying,
                "contract": sym,
                "expiry": c.expiry,
                "days_to_expiry": c.days_to_expiry(as_of),
                "T": round(c.year_fraction(as_of), 5),
                "close": round(float(r[sym]), 4),
                "volume": float(volumes.loc[d, sym]),
                "front": round(float(r["FRONT"]), 4) if pd.notna(r["FRONT"]) else None,
            })
    long = pd.DataFrame(rows).sort_values(["date", "T"]).reset_index(drop=True)
    long.to_csv(CLEAN / "curve_long.csv", index=False)
    print(f"wrote {CLEAN / 'curve_long.csv'}  ({len(long)} rows)")

    # ---- show the most recent curve as a table ----
    last = full.index.max()
    snap = long[long["date"] == last]
    print(f"\n=== futures curve on {last.date()} ===")
    print(f"{'contract':12s} {'expiry':12s} {'DTE':>4s} {'T(yr)':>7s} {'price':>9s}  {'vs front':>9s}")
    fr = float(full.loc[last, "FRONT"])
    for _, x in snap.iterrows():
        print(f"{x['contract']:12s} {str(x['expiry']):12s} {x['days_to_expiry']:4d} "
              f"{x['T']:7.4f} {x['close']:9.2f}  {x['close'] - fr:+9.2f}")
    print(f"{'FRONT (GC=F)':12s} {'':12s} {'':>4s} {'':>7s} {fr:9.2f}")

    shape = "CONTANGO" if snap["close"].is_monotonic_increasing else "not cleanly monotonic"
    print(f"\ncurve shape: {shape}")


if __name__ == "__main__":
    build()
