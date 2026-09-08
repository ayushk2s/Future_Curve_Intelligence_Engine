"""
Step 8 — REGIME DETECTION  (blueprint section 17)

A spread that mean-reverts in calm markets can trend hard in a stressed one.
So every signal must be conditioned on the current regime.

Two views:
  regime_vol    calm / normal / stressed   -- from a POINT-IN-TIME rolling
                percentile of realised volatility (no look-ahead)
  regime_trend  up / range / down          -- from the 20-day return
  regime_cluster (descriptive only) KMeans(3) on [vol, 20d return, carry level],
                fit on the whole sample -- used for the dashboard, NOT the backtest

Output: data/clean/regime.csv

Run:  python src/regime.py
"""

import pathlib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from _paths import CLEAN_DIR as CLEAN
RV_WIN = 20            # realised-vol window (trading days)
PCTILE_WIN = 120       # window for the rolling percentile of vol
TREND_WIN = 20
TREND_BAND = 0.03      # +/-3% over 20d = "trending"


def build() -> None:
    panel = pd.read_csv(CLEAN / "panel_prices.csv", parse_dates=["date"]).set_index("date")
    fv = pd.read_csv(CLEAN / "fairvalue.csv", parse_dates=["date"]).set_index("date")

    # use the front / anchor contract for the underlying's own vol & trend
    anchor = panel["GCV26.CMX"].dropna()
    ret = np.log(anchor).diff()

    rv = ret.rolling(RV_WIN).std() * np.sqrt(252)          # annualised realised vol
    # point-in-time percentile: rank of today's vol within the trailing window
    rv_pctile = rv.rolling(PCTILE_WIN, min_periods=40).apply(
        lambda w: (w.iloc[-1] >= w).mean(), raw=False)

    trend = anchor / anchor.shift(TREND_WIN) - 1.0

    out = pd.DataFrame(index=anchor.index)
    out["realised_vol"] = rv
    out["vol_pctile"] = rv_pctile
    out["ret_20d"] = trend

    out["regime_vol"] = np.select(
        [rv_pctile < 0.34, rv_pctile < 0.67],
        ["calm", "normal"], default="stressed")
    out.loc[rv_pctile.isna(), "regime_vol"] = "normal"

    out["regime_trend"] = np.select(
        [trend > TREND_BAND, trend < -TREND_BAND],
        ["up", "down"], default="range")

    # descriptive cluster (dashboard only)
    feat = pd.DataFrame({
        "rv": rv, "ret20": trend,
        "carry": fv["implied_carry"].reindex(anchor.index),
    }).dropna()
    if len(feat) > 20:
        Xs = StandardScaler().fit_transform(feat.values)
        km = KMeans(n_clusters=3, n_init=10, random_state=0).fit(Xs)
        lab = pd.Series(km.labels_, index=feat.index)
        # name clusters by their mean realised vol: 0=calm .. 2=stressed
        order = feat.groupby(lab)["rv"].mean().sort_values().index.tolist()
        rename = {old: nm for old, nm in zip(order, ["cluster_calm", "cluster_mid", "cluster_hot"])}
        out["regime_cluster"] = lab.map(rename).reindex(out.index)

    out.to_csv(CLEAN / "regime.csv")
    print(f"wrote {CLEAN / 'regime.csv'}  ({len(out)} rows)\n")
    print("regime_vol distribution:")
    print(out["regime_vol"].value_counts().to_string())
    print("\nregime_trend distribution:")
    print(out["regime_trend"].value_counts().to_string())
    last = out.iloc[-1]
    print(f"\nlatest {out.index.max().date()}: "
          f"vol={last['realised_vol']:.3f} (pctile {last['vol_pctile']:.2f}) "
          f"-> {last['regime_vol'].upper()} / {last['regime_trend'].upper()}"
          f"  [{last.get('regime_cluster', 'n/a')}]")


if __name__ == "__main__":
    build()
