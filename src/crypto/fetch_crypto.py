"""
CRYPTO DATA LAYER  (blueprint section 7, crypto adapter -- section 5 BTC/ETH)

Source: Deribit public API (no key). Writes the same immutable-raw pattern as
the gold adapter, under data/crypto/<CCY>/raw/ :

  <INSTRUMENT>.csv   date, open, high, low, close, volume   (dated futures + perp)
  _index.csv         date, index                            (true spot index)
  _funding.csv       date, funding_8h, funding_ann          (perpetual funding)

Curve instruments chosen: PERPETUAL + a spread of monthly/quarterly expiries.

Run:  python src/crypto/fetch_crypto.py BTC
      python src/crypto/fetch_crypto.py ETH
"""

import io
import json
import sys
import time
import pathlib
import urllib.request
import datetime as dt

import pandas as pd

API = "https://www.deribit.com/api/v2/public/"
DAY_MS = 24 * 3600 * 1000


def _get(path: str):
    req = urllib.request.Request(API + path, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))["result"]
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))


def pick_curve_instruments(ccy: str) -> list[str]:
    inst = _get(f"get_instruments?currency={ccy}&kind=future&expired=false")
    inst = [i for i in inst if i["instrument_name"] != f"{ccy}-PERPETUAL"]
    inst.sort(key=lambda x: x["expiration_timestamp"])
    # keep the monthly/quarterly ladder, skip the daily/weekly noise
    keep = [i for i in inst if i.get("settlement_period") == "month"]
    names = [i["instrument_name"] for i in keep]
    return [f"{ccy}-PERPETUAL"] + names


def fetch_ohlc(instrument: str, days: int = 400) -> pd.DataFrame:
    now = int(time.time() * 1000)
    start = now - days * DAY_MS
    r = _get(f"get_tradingview_chart_data?instrument_name={instrument}"
             f"&start_timestamp={start}&end_timestamp={now}&resolution=1D")
    if not r or r.get("status") == "no_data" or not r.get("ticks"):
        return pd.DataFrame()
    df = pd.DataFrame({
        "date": pd.to_datetime(r["ticks"], unit="ms").normalize(),
        "open": r["open"], "high": r["high"], "low": r["low"],
        "close": r["close"], "volume": r["volume"],
    })
    return df[df["close"] > 0].set_index("date")


def fetch_funding_and_index(ccy: str, days: int = 400):
    """Deribit's funding-rate history rows carry index_price too -> get both here."""
    now = int(time.time() * 1000)
    step = 25 * DAY_MS
    t = now - days * DAY_MS
    rows = []
    while t < now:
        r = _get(f"get_funding_rate_history?instrument_name={ccy}-PERPETUAL"
                 f"&start_timestamp={t}&end_timestamp={min(t+step, now)}")
        for x in (r or []):
            rows.append((x["timestamp"], x.get("interest_8h", 0.0), x.get("index_price")))
        t += step
    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    f = pd.DataFrame(rows, columns=["ts", "funding_8h", "index_price"]).drop_duplicates("ts")
    f["date"] = pd.to_datetime(f["ts"], unit="ms").dt.normalize()

    daily = f.groupby("date")["funding_8h"].mean().to_frame()
    daily["funding_ann"] = daily["funding_8h"] * 3 * 365       # 3 windows/day
    idx = f.groupby("date")["index_price"].last().rename("index").to_frame()
    idx = idx[idx["index"] > 0]
    return daily, idx


def main() -> None:
    ccy = (sys.argv[1] if len(sys.argv) > 1 else "BTC").upper()
    raw = pathlib.Path(__file__).resolve().parents[2] / "data" / "crypto" / ccy / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    instruments = pick_curve_instruments(ccy)
    print(f"{ccy} curve instruments: {instruments}\n")

    for name in instruments:
        df = fetch_ohlc(name)
        if df.empty:
            print(f"  {name:18s} -> no data, skipped")
            continue
        safe = name.replace("-", "_")
        (raw / f"{safe}.csv").write_text(df.to_csv())
        print(f"  {name:18s} -> {len(df):3d} bars  {df.index.min().date()} .. {df.index.max().date()}"
              f"  last {df['close'].iloc[-1]:.1f}")

    fund, idx = fetch_funding_and_index(ccy)
    if idx.empty:
        perp = pd.read_csv(raw / f"{ccy}_PERPETUAL.csv", parse_dates=["date"]).set_index("date")
        idx = perp[["close"]].rename(columns={"close": "index"})
        print("\n  index: FELL BACK to perpetual close")
    idx.to_csv(raw / "_index.csv")
    print(f"\n  _index.csv  -> {len(idx)} rows, last {idx['index'].iloc[-1]:.1f}")

    fund.to_csv(raw / "_funding.csv")
    print(f"  _funding.csv -> {len(fund)} rows, last 8h {fund['funding_8h'].iloc[-1]:.6f} "
          f"({fund['funding_ann'].iloc[-1]*100:+.2f}% ann)")


if __name__ == "__main__":
    main()
