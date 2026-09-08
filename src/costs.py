"""
Step 10 — COST & LIQUIDITY MODEL  (blueprint section 20)

Yahoo gives no bid/ask, so execution cost is modelled from tick size + liquidity
tier (median volume). COMEX gold: 100 troy oz/contract, min tick $0.10 = $10.

Per single-contract ONE-WAY cost (in $ per contract):
    half_spread  = ticks_by_tier * $10 / 2
    slippage     = 0.5 tick * $10
    commission   = $2.50

A calendar-spread ROUND TRIP touches 2 legs, in and out  = 4 fills.

Everything is also returned in GOLD POINTS (divide $ by 100) so it can be
compared directly against a spread's expected move in points.

Run:  python src/costs.py
"""

import pathlib
import pandas as pd

from _paths import CLEAN_DIR as CLEAN
CONTRACT_MULT = 100.0        # oz per contract
TICK_VALUE = 10.0            # $ per tick ($0.10 * 100 oz)
COMMISSION = 2.50            # $ per contract per side

# ticks of bid/ask spread assumed, by liquidity tier
TIER_TICKS = {"deep": 1.0, "ok": 2.0, "thin": 4.0}


def liquidity_tiers() -> dict:
    """Assign each contract a tier from its median volume over the sample."""
    long = pd.read_csv(CLEAN / "curve_long.csv", parse_dates=["date"])
    medv = long.groupby("contract")["volume"].median()
    tiers = {}
    for sym, v in medv.items():
        tiers[sym] = "deep" if v >= 20000 else ("ok" if v >= 3000 else "thin")
    return tiers, medv.to_dict()


def one_way_cost_usd(sym: str, tiers: dict) -> float:
    ticks = TIER_TICKS[tiers[sym]]
    half_spread = ticks * TICK_VALUE / 2.0
    slippage = 0.5 * TICK_VALUE
    return half_spread + slippage + COMMISSION


def spread_roundtrip_cost(sym_far: str, sym_near: str, tiers: dict) -> dict:
    """Cost to open AND close a 1-lot calendar spread (both legs)."""
    per_leg_one_way = one_way_cost_usd(sym_far, tiers) + one_way_cost_usd(sym_near, tiers)
    usd = per_leg_one_way * 2.0          # entry + exit
    return {"usd": round(usd, 2), "points": round(usd / CONTRACT_MULT, 3)}


if __name__ == "__main__":
    tiers, medv = liquidity_tiers()
    print("liquidity tiers (median volume over sample):")
    for sym in ["GCV26.CMX", "GCZ26.CMX", "GCG27.CMX", "GCJ27.CMX", "GCM27.CMX"]:
        print(f"  {sym:12s} medvol {medv[sym]:9.0f}  -> {tiers[sym]}")

    print("\ncalendar-spread round-trip cost (open+close, 1 lot):")
    pairs = [("GCZ26.CMX", "GCV26.CMX", "cs_Z_V"),
             ("GCG27.CMX", "GCZ26.CMX", "cs_G_Z"),
             ("GCJ27.CMX", "GCG27.CMX", "cs_J_G"),
             ("GCM27.CMX", "GCJ27.CMX", "cs_M_J")]
    for far, near, name in pairs:
        c = spread_roundtrip_cost(far, near, tiers)
        print(f"  {name:8s} {far[2:5]}/{near[2:5]:4s}  ${c['usd']:7.2f}  = {c['points']:.3f} gold points")
    print("\ncompare 'points' above to a spread's std (~4 pts): if expected capture")
    print("after costs isn't clearly positive, section 18 says it is NOT a trade.")
