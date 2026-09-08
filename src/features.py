"""
Step 5 — CORE CURVE FEATURES  (blueprint section 10)

From the clean curve panel, compute the numbers the modeling layer actually
reasons about. All of these are INTER-CONTRACT (no external spot needed):

  basis_<c>     = F(c) - F(anchor)          anchor = GCV26 (nearest expiry)
  basis_pct_<c> = basis / F(anchor)
  cs_<a>_<b>    = F(a) - F(b)               adjacent calendar spreads, later - earlier
  slope_ann     = (F_far - F_near) / (T_far - T_near)     $ per year of maturity
  curvature     = F(belly) - [straight line from near to far, read at belly's T]
  level         = mean of the 5 contract prices

Output: data/clean/features.csv  (one row per date)

Run:  python src/features.py
"""

import pathlib
import pandas as pd

from _paths import CLEAN_DIR as CLEAN

# contract symbols, near -> far
V = "GCV26.CMX"   # Oct 2026  -- ANCHOR (nearest expiry, closest to spot)
Z = "GCZ26.CMX"   # Dec 2026
G = "GCG27.CMX"   # Feb 2027  -- belly, used for curvature
J = "GCJ27.CMX"   # Apr 2027
M = "GCM27.CMX"   # Jun 2027  -- far end
ORDER = [V, Z, G, J, M]

def tag(sym: str) -> str:
    return sym[2:5]          # "GCV26.CMX" -> "V26"


def build() -> None:
    long = pd.read_csv(CLEAN / "curve_long.csv", parse_dates=["date"])

    # pivot the tidy frame into date x contract matrices
    px = long.pivot(index="date", columns="contract", values="close")
    T = long.pivot(index="date", columns="contract", values="T")

    f = pd.DataFrame(index=px.index)

    # --- basis vs the nearest contract ---
    anchor = px[V]
    for sym in ORDER:
        f[f"basis_{tag(sym)}"] = px[sym] - anchor
        f[f"basis_pct_{tag(sym)}"] = (px[sym] - anchor) / anchor

    # --- adjacent calendar spreads (later minus earlier -> positive = contango) ---
    f["cs_Z_V"] = px[Z] - px[V]
    f["cs_G_Z"] = px[G] - px[Z]
    f["cs_J_G"] = px[J] - px[G]
    f["cs_M_J"] = px[M] - px[J]

    # --- slope: annualised rise of the whole curve, near end to far end ---
    f["slope_ann"] = (px[M] - px[V]) / (T[M] - T[V])

    # --- curvature: belly vs the straight line joining near and far ---
    w = (T[G] - T[V]) / (T[M] - T[V])           # where the belly sits along the chord
    line_at_belly = px[V] + w * (px[M] - px[V])
    f["curvature"] = px[G] - line_at_belly

    # --- level: overall height ---
    f["level"] = px[ORDER].mean(axis=1)

    f = f.dropna()
    f.to_csv(CLEAN / "features.csv")
    print(f"wrote {CLEAN / 'features.csv'}  ({len(f)} rows, "
          f"{f.index.min().date()} .. {f.index.max().date()})\n")

    # --- what do these look like? mean/std here IS the input to z-scores next ---
    show = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J", "curvature", "slope_ann"]
    print("summary over the whole sample:")
    print(f"{'feature':12s} {'mean':>10s} {'std':>10s} {'min':>10s} {'max':>10s} {'last':>10s}")
    for c in show:
        s = f[c]
        print(f"{c:12s} {s.mean():10.3f} {s.std():10.3f} {s.min():10.3f} "
              f"{s.max():10.3f} {s.iloc[-1]:10.3f}")

    print(f"\nlast date {f.index.max().date()}:")
    last = f.iloc[-1]
    print(f"  curve level     {last['level']:.2f}")
    print(f"  slope (ann.)    {last['slope_ann']:.2f} $/yr")
    print(f"  curvature       {last['curvature']:+.2f}  "
          f"({'concave / front steeper' if last['curvature'] < 0 else 'convex / belly rich'})")
    print(f"  calendar spreads: Z-V {last['cs_Z_V']:.2f}  G-Z {last['cs_G_Z']:.2f}  "
          f"J-G {last['cs_J_G']:.2f}  M-J {last['cs_M_J']:.2f}")


if __name__ == "__main__":
    build()
