"""
Step 7 — DEVIATION / Z-SCORE ENGINE  (blueprint section 11)

Two kinds of "abnormal" are computed for every spread and curve feature:

  z_hist_<x>  = (x_t - rolling_mean) / rolling_std
                "far from its own recent history"
  z_fair_<x>  = (fair-value deviation_t - its rolling_mean) / rolling_std
                "far from where the carry model says it should be"

CRUCIAL (blueprint section 28 - look-ahead bias): the rolling mean/std used at
day t only see data up to day t-1  -> .rolling(win).mean().shift(1).
Every downstream signal and backtest depends on this being honest.

anomaly_<x> = 1 when |z_hist| >= Z_FLAG.

Output: data/clean/deviation.csv

Run:  python src/deviation.py
"""

import pathlib
import numpy as np
import pandas as pd

from _paths import CLEAN_DIR as CLEAN

ROLL_WIN = 60      # ~3 trading months
MIN_OBS = 20
Z_FLAG = 2.0

# features whose deviation matters
HIST_SERIES = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J", "curvature", "slope_ann",
               "basis_Z26", "basis_G27", "basis_J27", "basis_M27"]
FAIR_SERIES = ["devspread_cs_Z_V", "devspread_cs_G_Z", "devspread_cs_J_G", "devspread_cs_M_J"]


def pit_z(s: pd.Series, win: int = ROLL_WIN, min_obs: int = MIN_OBS) -> pd.Series:
    """Point-in-time z-score: stats at t use only data up to t-1."""
    mean = s.rolling(win, min_periods=min_obs).mean().shift(1)
    std = s.rolling(win, min_periods=min_obs).std().shift(1)
    z = (s - mean) / std.replace(0.0, np.nan)          # guard std == 0 -> no inf
    return z.replace([np.inf, -np.inf], np.nan)


def build() -> None:
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    fv = pd.read_csv(CLEAN / "fairvalue.csv", parse_dates=["date"]).set_index("date")
    df = feats.join(fv, how="inner")

    out = pd.DataFrame(index=df.index)

    for c in HIST_SERIES:
        out[f"z_hist_{c}"] = pit_z(df[c])
        out[f"anomaly_{c}"] = (out[f"z_hist_{c}"].abs() >= Z_FLAG).astype("Int64")

    for c in FAIR_SERIES:
        out[f"z_fair_{c}"] = pit_z(df[c])

    # carry regime context: is the implied carry rate itself unusually high/low?
    out["z_carry"] = pit_z(df["implied_carry"])

    out.to_csv(CLEAN / "deviation.csv")
    n_anom = int(out[[c for c in out.columns if c.startswith("anomaly_")]].sum().sum())
    print(f"wrote {CLEAN / 'deviation.csv'}  ({len(out)} rows, {n_anom} anomaly flags total)\n")

    last = out.iloc[-1]
    d = out.index.max().date()
    print(f"z-scores on {d} (|z| >= {Z_FLAG} = flagged):")
    for c in HIST_SERIES:
        z = last[f"z_hist_{c}"]
        mark = "  <-- ANOMALY" if abs(z) >= Z_FLAG else ""
        print(f"  z_hist {c:12s} {z:+6.2f}{mark}")
    print()
    for c in FAIR_SERIES:
        print(f"  z_fair {c:22s} {last[f'z_fair_{c}']:+6.2f}")
    print(f"\n  z_carry (implied carry rate vs its history) {last['z_carry']:+.2f}")
    print("\n  reading: high z_hist on spreads + high z_carry  ==>  the steepness is")
    print("  mostly a real carry move, not a mispricing.  z_fair (vs carry curve) is")
    print("  the cleaner anomaly signal.")


if __name__ == "__main__":
    build()
