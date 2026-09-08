"""
Step 6 — FAIR-VALUE CURVE  (blueprint section 12)

Instead of asking "is today's spread far from its 60-day average?" (that's the
z-score engine, section 11), this asks a better question: "given a smooth
cost-of-carry curve fitted to TODAY's prices, which contracts sit rich or cheap
versus that smooth curve?"

Model (carry / no-arbitrage, Lesson 2):
    F(T) = S * exp(c * T)
  => ln F(T) = ln S + c * T          <-- a straight line in (T, ln F)

So each day, regress ln(price) on T across the 5 contracts:
    slope     = c  = implied net carry rate (r + s - y), annualised
    intercept = ln S_implied  (an implied spot, backed out from the curve)//
Fair price of each contract = exp(intercept + c * T).
Deviation = actual - fair.  Positive = contract trades rich to the carry curve.

A SMOOTHED carry rate (rolling median) is also kept so a single noisy day
doesn't move "fair value" around.

Output: data/clean/fairvalue.csv

Run:  python src/fairvalue.py
"""

import pathlib
import numpy as np
import pandas as pd

from _paths import CLEAN_DIR as CLEAN

V, Z, G, J, M = "GCV26.CMX", "GCZ26.CMX", "GCG27.CMX", "GCJ27.CMX", "GCM27.CMX"
ORDER = [V, Z, G, J, M]
def tag(s): return s[2:5]

CARRY_SMOOTH_WIN = 10          # trading days to smooth the implied carry rate


def fit_carry_curve(prices: pd.Series, tenors: pd.Series):
    """
    One day's fit. prices, tenors are length-5.
    Returns (implied_spot, carry_rate, r2, fair_prices ndarray).
    """
    y = np.log(prices.values.astype(float))
    x = tenors.values.astype(float)
    A = np.vstack([np.ones_like(x), x]).T           # [1, T]
    (intercept, slope), *_ = np.linalg.lstsq(A, y, rcond=None)
    fair_log = intercept + slope * x
    ss_res = np.sum((y - fair_log) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return np.exp(intercept), slope, r2, np.exp(fair_log)


def build() -> None:
    long = pd.read_csv(CLEAN / "curve_long.csv", parse_dates=["date"])
    px = long.pivot(index="date", columns="contract", values="close")[ORDER]
    T = long.pivot(index="date", columns="contract", values="T")[ORDER]

    recs = []
    for d in px.index:
        s_imp, c, r2, fair = fit_carry_curve(px.loc[d], T.loc[d])
        row = {"date": d, "implied_spot": s_imp, "implied_carry": c, "fit_r2": r2}
        for sym, fv in zip(ORDER, fair):
            row[f"fair_{tag(sym)}"] = fv
            row[f"dev_{tag(sym)}"] = px.loc[d, sym] - fv       # actual - fair
        recs.append(row)

    fv = pd.DataFrame(recs).set_index("date")

    # smoothed carry rate -> a more stable "fair curve" (point-in-time: no future data)
    fv["carry_smooth"] = (fv["implied_carry"]
                          .rolling(CARRY_SMOOTH_WIN, min_periods=3).median())

    # fair calendar spreads from the fitted curve, and how far actual spreads sit from them
    fair_cols = {tag(s): fv[f"fair_{tag(s)}"] for s in ORDER}
    fv["fair_cs_Z_V"] = fair_cols["Z26"] - fair_cols["V26"]
    fv["fair_cs_G_Z"] = fair_cols["G27"] - fair_cols["Z26"]
    fv["fair_cs_J_G"] = fair_cols["J27"] - fair_cols["G27"]
    fv["fair_cs_M_J"] = fair_cols["M27"] - fair_cols["J27"]

    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    for pair in ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]:
        fv[f"devspread_{pair}"] = feats[pair] - fv[f"fair_{pair}"]

    fv.to_csv(CLEAN / "fairvalue.csv")
    print(f"wrote {CLEAN / 'fairvalue.csv'}  ({len(fv)} rows)\n")

    print("implied carry rate (r + s - y), annualised:")
    print(f"  mean {fv['implied_carry'].mean():.4f}   "
          f"std {fv['implied_carry'].std():.4f}   "
          f"last {fv['implied_carry'].iloc[-1]:.4f}   "
          f"({fv['implied_carry'].iloc[-1]*100:.2f}% per year)")
    print(f"curve fit R^2: mean {fv['fit_r2'].mean():.5f}  "
          f"(1.0 = carry model explains the curve perfectly)")

    last = fv.iloc[-1]
    print(f"\nrich/cheap vs fair carry curve on {fv.index.max().date()}:")
    for s in ORDER:
        d = last[f"dev_{tag(s)}"]
        print(f"  {tag(s)}  actual {px.loc[fv.index.max(), s]:8.2f}   "
              f"fair {last[f'fair_{tag(s)}']:8.2f}   dev {d:+7.2f}  "
              f"{'RICH' if d > 0 else 'cheap'}")


if __name__ == "__main__":
    build()
