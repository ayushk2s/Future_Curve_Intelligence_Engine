"""
Step 9 — CONVERGENCE STUDY  (blueprint sections 27, 29)

The signal engine needs to answer: "the spread is X z-scores from its mean --
historically, how often did it revert, and how much did it move over the next
H days?"

Two outputs:

1. OU / AR(1) HALF-LIFE per spread:
      s_t - mu = rho * (s_{t-1} - mu) + noise
      half_life = -ln(2) / ln(rho)     (trading days to close half the gap)

2. EMPIRICAL REVERSION TABLE (pooled across the 4 adjacent spreads, since
   Lesson: they share one driver). For entry buckets of z_hist, over H days:
      p_revert            = P(spread moved toward its mean)
      mean_gap_captured   = average fraction of the (t) gap-to-mean closed by t+H
                            (1.0 = fully reverted, <0 = widened further)

CRUCIAL: z is point-in-time (from deviation.csv, already shifted). Forward
returns are simply future minus present -- no look-ahead in the label.

Output: data/clean/convergence.csv  (the empirical table)
        + printed half-lives
Also exposes lookup helpers used by signals.py.

Run:  python src/convergence.py
"""

import pathlib
import numpy as np
import pandas as pd

from _paths import CLEAN_DIR as CLEAN
SPREADS = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]
HORIZONS = [5, 10, 20]
Z_BUCKETS = [(-99, -2), (-2, -1.5), (-1.5, -1), (-1, 1), (1, 1.5), (1.5, 2), (2, 99)]


def ar1_half_life(s: pd.Series):
    s = s.dropna()
    mu = s.mean()
    x = (s - mu).values
    x0, x1 = x[:-1], x[1:]
    rho = float(np.dot(x0, x1) / np.dot(x0, x0))
    if not (0 < rho < 1):
        return np.nan, rho
    return -np.log(2) / np.log(rho), rho


def build() -> None:
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    dev = pd.read_csv(CLEAN / "deviation.csv", parse_dates=["date"]).set_index("date")

    print("AR(1) mean-reversion half-life (trading days):")
    hl = {}
    for sp in SPREADS:
        h, rho = ar1_half_life(feats[sp])
        hl[sp] = h
        print(f"  {sp:8s}  rho={rho:.3f}  half-life={h:.1f} days")
    print(f"  --> pooled median half-life ~ {np.nanmedian(list(hl.values())):.1f} days\n")

    # rolling mean used for 'gap to mean' (point-in-time, same window as deviation.py)
    rows = []
    for sp in SPREADS:
        mu_pit = feats[sp].rolling(60, min_periods=20).mean().shift(1)
        gap0 = feats[sp] - mu_pit                       # signed distance from mean at t
        z = dev[f"z_hist_{sp}"]
        for H in HORIZONS:
            fwd = feats[sp].shift(-H) - feats[sp]       # change over next H days
            gap_captured = -fwd / gap0                  # >0 means moved toward mean
            moved_toward = (np.sign(fwd) != np.sign(gap0)) & gap0.notna() & fwd.notna()
            d = pd.DataFrame({"z": z, "gap_captured": gap_captured,
                              "toward": moved_toward.astype(float),
                              "fwd": fwd, "gap0": gap0}).dropna()
            for lo, hi in Z_BUCKETS:
                m = (d["z"] >= lo) & (d["z"] < hi)
                if m.sum() < 5:
                    continue
                rows.append({
                    "spread": sp, "horizon": H, "z_lo": lo, "z_hi": hi,
                    "n": int(m.sum()),
                    "p_revert": round(d.loc[m, "toward"].mean(), 3),
                    "mean_gap_captured": round(d.loc[m, "gap_captured"].clip(-3, 3).mean(), 3),
                    "mean_fwd_chg": round(d.loc[m, "fwd"].mean(), 3),
                })

    tbl = pd.DataFrame(rows)
    tbl.to_csv(CLEAN / "convergence.csv", index=False)
    print(f"wrote {CLEAN / 'convergence.csv'}  ({len(tbl)} bucket rows)\n")

    # pooled view (all spreads together) at H=10 -- what the signal engine leans on
    pooled = (tbl[tbl["horizon"] == 10]
              .groupby(["z_lo", "z_hi"])
              .apply(lambda g: pd.Series({
                  "n": int(g["n"].sum()),
                  "p_revert": round(np.average(g["p_revert"], weights=g["n"]), 3),
                  "gap_captured": round(np.average(g["mean_gap_captured"], weights=g["n"]), 3),
              }), include_groups=False)
              .reset_index())
    print("pooled reversion over next 10 days, by entry z bucket:")
    print(pooled.to_string(index=False))
    print("\nread: entry |z|>=2 with p_revert well above 0.5 and gap_captured>0")
    print("means the deviation historically paid to fade.")


if __name__ == "__main__":
    build()
