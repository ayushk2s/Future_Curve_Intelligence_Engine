"""
Step 13 — WALK-FORWARD BACKTEST  (blueprint section 20)

Event backtest on calendar-spread trades. Three entry rules, same exit &
risk logic, to see what each layer of discipline is worth:

  A  naive_zhist  enter when |z_hist| >= 2   (fade history, NO cost/regime gate)
  B  fairvalue    enter when |z_fair| >= 1.25 and expected net > 0
  C  gated        enter only on signals.trade_candidate
                  (fair value + regime filter + model agreement + score)
  D  model_momo   enter WITH the GBR forecast: |gbr_pred| >= 0.6, dir = sign(gbr_pred)
                  (a-priori rationale: convergence study showed spreads trended,
                   and GBR had positive out-of-sample directional skill)

Exit fade strategies (A/B/C): reverted (|z_fair| < 0.4) | max hold 25d | stop -3 pts
Exit momentum strategy (D):   opposite GBR sign | max hold 25d | stop -3 pts
Both also exit if near leg within 8 days of expiry.
Cost: round-trip charged in points at exit (from costs.py, via signals.csv).
No look-ahead: z_fair uses lagged rolling stats; GBR preds are walk-forward OOS.

P&L is per 1-lot spread; 1 point = $100 (100 oz contract).

Outputs (data/output/):
  bt_trades_A.csv / _B.csv / _C.csv
  bt_equity.csv        (date, equity_A, equity_B, equity_C  -- realised, $)
  bt_metrics.csv       (one row per strategy)

Run:  python src/backtest.py
"""

import pathlib
import numpy as np
import pandas as pd

from _paths import CLEAN_DIR as CLEAN, OUT_DIR as OUT

SPREADS = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]
POINT_USD = 100.0
MAX_CONCURRENT = 3
MAX_HOLD = 25
STOP_PTS = 3.0
REVERT_Z = 0.4
DTE_EXIT = 8
NOTIONAL = 50_000.0        # assumed book size, for % return / Sharpe context


def load():
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    sig = pd.read_csv(CLEAN / "signals.csv", parse_dates=["date"])
    dev = pd.read_csv(CLEAN / "deviation.csv", parse_dates=["date"]).set_index("date")
    return feats, sig, dev


def entry_mask(sig: pd.DataFrame, strat: str) -> pd.Series:
    if strat == "A":
        return sig["z_hist"].abs() >= 2.0
    if strat == "B":
        return (sig["z_fair"].abs() >= 1.25) & (sig["exp_net_pts"] > 0)
    if strat == "D":
        return sig["gbr_pred"].abs() >= 0.6
    return sig["trade_candidate"].astype(bool)      # C


def direction_for(sig_row, strat: str) -> int:
    if strat == "A":
        return int(-np.sign(sig_row["z_hist"]))
    if strat == "D":
        return int(np.sign(sig_row["gbr_pred"]))    # trade WITH the forecast
    return int(sig_row["direction"])


def run_strategy(feats, sig, dev, strat: str):
    sig = sig.copy()
    sig["enter"] = entry_mask(sig, strat)
    by_key = {(r["date"], r["spread"]): r for _, r in sig.iterrows()}
    dates = feats.index.tolist()
    zf = {sp: dev[f"z_fair_devspread_{sp}"] for sp in SPREADS}

    open_pos = []          # dicts
    trades = []
    realised = 0.0
    equity_rows = []

    for d in dates:
        # ---- manage exits ----
        still = []
        for p in open_pos:
            sp = p["spread"]
            if d not in feats.index:
                still.append(p); continue
            spread_now = feats.loc[d, sp]
            held = (d - p["entry_date"]).days
            pnl_pts_mtm = p["dir"] * (spread_now - p["entry_spread"])
            z_now = zf[sp].get(d, np.nan)
            row = by_key.get((d, sp))
            ndte = row["near_dte"] if row is not None and pd.notna(row["near_dte"]) else 99

            gbr_now = row["gbr_pred"] if row is not None else np.nan

            reason = None
            if strat == "D":
                if np.isfinite(gbr_now) and np.sign(gbr_now) == -p["dir"]:
                    reason = "signal_flip"
            else:
                if np.isfinite(z_now) and abs(z_now) < REVERT_Z:
                    reason = "reverted"
            if reason is None:
                if held >= MAX_HOLD:
                    reason = "max_hold"
                elif pnl_pts_mtm <= -STOP_PTS:
                    reason = "stop"
                elif ndte <= DTE_EXIT:
                    reason = "expiry"

            if reason:
                pnl_pts = pnl_pts_mtm - p["cost_pts"]
                realised += pnl_pts * POINT_USD
                trades.append({**{k: p[k] for k in ("spread", "entry_date", "entry_spread", "dir", "cost_pts")},
                               "exit_date": d, "exit_spread": spread_now, "held_days": held,
                               "pnl_pts": round(pnl_pts, 3), "pnl_usd": round(pnl_pts * POINT_USD, 2),
                               "exit_reason": reason, "regime_vol_entry": p["regime_vol"]})
            else:
                still.append(p)
        open_pos = still

        # ---- entries ----
        todays = sig[(sig["date"] == d) & sig["enter"]].sort_values("signal_score", ascending=False)
        held_spreads = {p["spread"] for p in open_pos}
        for _, r in todays.iterrows():
            if len(open_pos) >= MAX_CONCURRENT:
                break
            if r["spread"] in held_spreads:
                continue
            dirn = direction_for(r, strat)
            if dirn == 0:
                continue
            open_pos.append({
                "spread": r["spread"], "entry_date": d,
                "entry_spread": float(feats.loc[d, r["spread"]]),
                "dir": dirn, "cost_pts": float(r["cost_pts"]),
                "regime_vol": r["regime_vol"],
            })
            held_spreads.add(r["spread"])

        # ---- mark equity (realised + open MTM) ----
        open_mtm = sum(p["dir"] * (feats.loc[d, p["spread"]] - p["entry_spread"]) * POINT_USD
                       for p in open_pos) if d in feats.index else 0.0
        equity_rows.append({"date": d, "realised": realised,
                            "equity": realised + open_mtm, "n_open": len(open_pos)})

    tr = pd.DataFrame(trades)
    eq = pd.DataFrame(equity_rows).set_index("date")
    return tr, eq


def metrics(tr: pd.DataFrame, eq: pd.DataFrame, strat: str) -> dict:
    if tr.empty:
        return {"strategy": strat, "n_trades": 0}
    wins = tr[tr["pnl_usd"] > 0]["pnl_usd"]
    losses = tr[tr["pnl_usd"] <= 0]["pnl_usd"]
    daily = eq["equity"].diff().dropna()
    dret = daily / NOTIONAL
    sharpe = (dret.mean() / dret.std() * np.sqrt(252)) if dret.std() > 0 else np.nan
    downside = dret[dret < 0].std()
    sortino = (dret.mean() / downside * np.sqrt(252)) if downside and downside > 0 else np.nan
    peak = eq["equity"].cummax()
    dd = (eq["equity"] - peak)
    return {
        "strategy": strat,
        "n_trades": len(tr),
        "win_rate": round((tr["pnl_usd"] > 0).mean(), 3),
        "total_pnl_usd": round(tr["pnl_usd"].sum(), 0),
        "avg_win": round(wins.mean(), 1) if len(wins) else 0.0,
        "avg_loss": round(losses.mean(), 1) if len(losses) else 0.0,
        "profit_factor": round(wins.sum() / abs(losses.sum()), 2) if losses.sum() != 0 else np.nan,
        "avg_hold_days": round(tr["held_days"].mean(), 1),
        "sharpe_ann": round(sharpe, 2),
        "sortino_ann": round(sortino, 2),
        "max_dd_usd": round(dd.min(), 0),
        "return_on_50k_pct": round(tr["pnl_usd"].sum() / NOTIONAL * 100, 2),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feats, sig, dev = load()

    labels = {"A": "naive z_hist fade", "B": "fair-value fade",
              "C": "gated (full discipline)", "D": "model momentum (trade WITH GBR)"}
    eqs, mrows = {}, []
    for strat in ["A", "B", "C", "D"]:
        tr, eq = run_strategy(feats, sig, dev, strat)
        tr.to_csv(OUT / f"bt_trades_{strat}.csv", index=False)
        eqs[strat] = eq["equity"].rename(f"equity_{strat}")
        m = metrics(tr, eq, strat)
        mrows.append(m)

        # P&L by regime
        if not tr.empty:
            byreg = tr.groupby("regime_vol_entry")["pnl_usd"].agg(["count", "sum"])
        else:
            byreg = "no trades"
        print(f"\n--- Strategy {strat} ({labels[strat]}) ---")
        for k, v in m.items():
            print(f"  {k:20s} {v}")
        print(f"  pnl by entry regime:\n{byreg}")

    pd.concat(eqs.values(), axis=1).to_csv(OUT / "bt_equity.csv")
    pd.DataFrame(mrows).to_csv(OUT / "bt_metrics.csv", index=False)
    print(f"\nwrote {OUT}/bt_metrics.csv, bt_equity.csv, bt_trades_*.csv")
    print("\nTAKEAWAY: compare A vs C. If the naive fade bleeds and the gated one")
    print("protects capital / trades rarely, the discipline layer is doing its job.")


if __name__ == "__main__":
    main()
