"""
Step 12 — SIGNAL & RISK ENGINE  (blueprint sections 18, 19)

For every (date, spread) build a decision record. The core principle from
section 18:  "contracts are close" is NOT a signal. The signal is that the
spread is abnormal versus a FAIR-VALUE model AND enough net edge survives
costs, regime and liquidity.

Pipeline per row:
  fair_gap   = actual_spread - fair_spread(carry curve)     [gold points]
  direction  = -sign(fair_gap)     (+1 = long spread, -1 = short spread; fade the deviation)
  model_agree= GBR forecast points in the same direction
  exp_gross  = 0.5 * |fair_gap|    (expect to close ~half the gap over the horizon)
  exp_net    = exp_gross - roundtrip_cost
  regime_mult= 1.0 calm/normal & range ; 0.5 stressed ; 0.6 strong trend
  adj_net    = exp_net * regime_mult * (1.0 if model_agree else 0.45)
  signal_score 0..100 = blend(adj_net vs spread vol, |z_fair|, model_agree,
                              liquidity, days-to-expiry comfort)
  trade_candidate = adj_net > 0  AND |z_fair| >= Z_FAIR_MIN  AND score >= SCORE_MIN
                    AND near_dte >= DTE_MIN

Output: data/clean/signals.csv   (every row; backtest derives its entry masks here)

Run:  python src/signals.py
"""

import pathlib
import numpy as np
import pandas as pd
from costs import liquidity_tiers, spread_roundtrip_cost

from _paths import CLEAN_DIR as CLEAN
SPREADS = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]
FAR_NEAR = {"cs_Z_V": ("GCZ26.CMX", "GCV26.CMX"), "cs_G_Z": ("GCG27.CMX", "GCZ26.CMX"),
            "cs_J_G": ("GCJ27.CMX", "GCG27.CMX"), "cs_M_J": ("GCM27.CMX", "GCJ27.CMX")}
NEAR_TAG = {"cs_Z_V": "V26", "cs_G_Z": "Z26", "cs_J_G": "G27", "cs_M_J": "J27"}

Z_FAIR_MIN = 1.25
SCORE_MIN = 45.0
DTE_MIN = 12
GAP_CLOSE_FRAC = 0.5     # expected fraction of the fair-value gap closed over the hold


def build() -> None:
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    fv = pd.read_csv(CLEAN / "fairvalue.csv", parse_dates=["date"]).set_index("date")
    dev = pd.read_csv(CLEAN / "deviation.csv", parse_dates=["date"]).set_index("date")
    reg = pd.read_csv(CLEAN / "regime.csv", parse_dates=["date"]).set_index("date")
    pred = pd.read_csv(CLEAN / "predictions.csv", parse_dates=["date"])
    long = pd.read_csv(CLEAN / "curve_long.csv", parse_dates=["date"])
    dte = long.pivot(index="date", columns="contract", values="days_to_expiry")
    dte.columns = [c[2:5] for c in dte.columns]

    tiers, medv = liquidity_tiers()
    cost_pts = {sp: spread_roundtrip_cost(*FAR_NEAR[sp], tiers)["points"] for sp in SPREADS}
    tier_rank = {"deep": 1.0, "ok": 0.6, "thin": 0.3}

    gbr = pred.pivot(index="date", columns="spread_name", values="gbr_pred")

    rows = []
    for sp in SPREADS:
        far, near = FAR_NEAR[sp]
        spread_vol = feats[sp].rolling(60, min_periods=20).std().shift(1)
        for d in feats.index:
            fair_gap = feats.loc[d, sp] - fv.loc[d, f"fair_{sp}"]
            zf = dev.loc[d, f"z_fair_devspread_{sp}"]
            zh = dev.loc[d, f"z_hist_{sp}"]
            g = gbr.loc[d, sp] if (d in gbr.index and sp in gbr.columns) else np.nan
            nd = dte.loc[d, NEAR_TAG[sp]] if d in dte.index else np.nan
            sv = spread_vol.loc[d]
            rv_reg = reg.loc[d, "regime_vol"] if d in reg.index else "normal"
            tr_reg = reg.loc[d, "regime_trend"] if d in reg.index else "range"

            if not np.isfinite(fair_gap):
                continue
            direction = -np.sign(fair_gap) if fair_gap != 0 else 0.0
            model_dir_pts = (g * direction) if np.isfinite(g) else 0.0
            model_agree = bool(model_dir_pts > 0)

            exp_gross = GAP_CLOSE_FRAC * abs(fair_gap)
            exp_net = exp_gross - cost_pts[sp]

            regime_mult = 1.0
            if rv_reg == "stressed":
                regime_mult *= 0.5
            if tr_reg in ("up", "down"):
                regime_mult *= 0.6
            adj_net = exp_net * regime_mult * (1.0 if model_agree else 0.45)

            # 0..100 score -- weighted mostly on conviction (|z_fair|), model
            # agreement and liquidity; the raw dollar edge on gold is tiny so it
            # only nudges the score.
            edge_term = np.tanh(max(adj_net, 0.0) / 1.0)
            z_term = min(abs(zf) / 3.0, 1.0) if np.isfinite(zf) else 0.0
            liq_term = tier_rank[tiers[far]] * tier_rank[tiers[near]]
            dte_term = 1.0 if (np.isfinite(nd) and nd >= DTE_MIN) else 0.0
            score = 100.0 * np.clip(
                0.30 * z_term + 0.20 * model_agree + 0.20 * liq_term
                + 0.15 * dte_term + 0.15 * edge_term, 0, 1)

            candidate = bool(
                (exp_net > 0) and np.isfinite(zf) and (abs(zf) >= Z_FAIR_MIN)
                and (score >= SCORE_MIN) and np.isfinite(nd) and (nd >= DTE_MIN))

            rows.append({
                "date": d, "spread": sp,
                "actual": round(float(feats.loc[d, sp]), 3),
                "fair": round(float(fv.loc[d, f"fair_{sp}"]), 3),
                "fair_gap": round(float(fair_gap), 3),
                "z_fair": round(float(zf), 3) if np.isfinite(zf) else np.nan,
                "z_hist": round(float(zh), 3) if np.isfinite(zh) else np.nan,
                "gbr_pred": round(float(g), 3) if np.isfinite(g) else np.nan,
                "direction": int(direction),
                "model_agree": model_agree,
                "regime_vol": rv_reg, "regime_trend": tr_reg,
                "cost_pts": cost_pts[sp],
                "exp_gross_pts": round(float(exp_gross), 3),
                "exp_net_pts": round(float(exp_net), 3),
                "adj_net_pts": round(float(adj_net), 3),
                "near_dte": int(nd) if np.isfinite(nd) else None,
                "signal_score": round(float(score), 1),
                "trade_candidate": candidate,
            })

    sig = pd.DataFrame(rows).sort_values(["date", "signal_score"], ascending=[True, False])
    sig.to_csv(CLEAN / "signals.csv", index=False)
    print(f"wrote {CLEAN / 'signals.csv'}  ({len(sig)} rows, "
          f"{int(sig['trade_candidate'].sum())} trade-candidate rows)\n")

    last = sig[sig["date"] == sig["date"].max()]
    print(f"=== signals on {sig['date'].max().date()} (ranked) ===")
    cols = ["spread", "actual", "fair", "fair_gap", "z_fair", "gbr_pred", "direction",
            "model_agree", "regime_vol", "adj_net_pts", "signal_score", "trade_candidate"]
    print(last[cols].to_string(index=False))
    cand = last[last["trade_candidate"]]
    if cand.empty:
        print("\nno trade candidates today -> engine says STAND ASIDE (edge<=cost or regime unfavourable).")
    else:
        for _, r in cand.iterrows():
            side = "LONG" if r["direction"] > 0 else "SHORT"
            print(f"\n  CANDIDATE: {side} {r['spread']}  score {r['signal_score']}  "
                  f"exp net {r['adj_net_pts']} pts (${r['adj_net_pts']*100:.0f}/lot)")


if __name__ == "__main__":
    build()
