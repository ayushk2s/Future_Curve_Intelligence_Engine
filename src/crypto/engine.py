"""
CRYPTO CURVE ENGINE  (blueprint sections 9-20, BTC/ETH adapter)

Reuses the gold engine's ideas but the tradeable object is the CRYPTO CARRY
DISLOCATION:

  qbasis_<T>  = F(dated) - F(perp)              [USD, the dated premium over perp]
  fair_qbasis = index * funding_ann_7d * T      [what funding says that premium
                                                 should be]
  gap         = qbasis - fair_qbasis            [dated future rich/cheap vs funding]

When a quarterly trades far richer than trailing funding implies -> short the
quarterly / long the perp (collect the excess basis as it converges). And vice
versa. This is a genuine, well-known basis trade; unlike gold, the dislocations
are large relative to fees.

Writes the SAME clean-CSV schema as the gold engine, under
data/crypto/<CCY>/clean/  and  data/crypto/<CCY>/output/ , so the dashboard can
read either market.

Run:  python src/crypto/engine.py BTC
      python src/crypto/engine.py ETH
"""

import sys
import pathlib
import datetime as dt

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]      # repo root
sys.path.insert(0, str(ROOT / "src"))
from fairvalue import fit_carry_curve          # noqa: E402
from deviation import pit_z                    # noqa: E402
from _paths import crypto_dir                  # noqa: E402

MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
          "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

# dated contracts to use for the curve (kept if they have >= 60 bars)
DATED = ["25SEP26", "25DEC26", "26MAR27", "25JUN27"]
ROLL_WIN, MIN_OBS = 45, 15
FUND_WIN = 7
Z_ENTER = 1.25
FEE_RATE = 0.0004          # 4 bps taker per leg per side (Deribit-ish)
MAX_HOLD, STOP_FRAC = 30, 0.9
POINT = 1.0               # already in USD per 1 unit of underlying
NOTIONAL = 50_000.0
TODAY = dt.date(2026, 9, 8)


def parse_expiry(tag: str) -> dt.date:
    d = int(tag[:2]); mon = MONTHS[tag[2:5]]; yr = 2000 + int(tag[5:7])
    return dt.date(yr, mon, d)


def load(ccy: str):
    raw = crypto_dir(ccy, "raw")
    perp = pd.read_csv(raw / f"{ccy}_PERPETUAL.csv", parse_dates=["date"]).set_index("date")["close"]
    idx = pd.read_csv(raw / "_index.csv", parse_dates=["date"]).set_index("date")["index"]
    fund = pd.read_csv(raw / "_funding.csv", parse_dates=["date"]).set_index("date")
    dated = {}
    for tag in DATED:
        f = raw / f"{ccy}_{tag}.csv"
        if not f.exists():
            continue
        s = pd.read_csv(f, parse_dates=["date"]).set_index("date")["close"]
        if len(s) >= 60:
            dated[tag] = s
    return perp, idx, fund, dated


def build(ccy: str) -> None:
    clean = crypto_dir(ccy, "clean")
    out = crypto_dir(ccy, "output")
    clean.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    perp, idx, fund, dated = load(ccy)
    tags = list(dated.keys())
    px = pd.DataFrame({"PERP": perp, **dated}).join(idx.rename("INDEX"), how="inner")
    px = px.dropna(subset=["PERP", "INDEX"])         # keep every day PERP+INDEX exist;
    #                                                 dated columns may be NaN early
    fund = fund.reindex(px.index).ffill()
    fund["funding_ann_7d"] = fund["funding_ann"].rolling(FUND_WIN, min_periods=2).mean()

    # days-to-expiry is pure calendar math -> defined for every date
    dte_df = pd.DataFrame(
        {t: [(parse_expiry(t) - d.date()).days for d in px.index] for t in tags},
        index=px.index)
    dte = {t: dte_df[t].values for t in tags}

    # ---------- features ----------
    f = pd.DataFrame(index=px.index)
    f["index"] = px["INDEX"]
    f["perp"] = px["PERP"]
    f["perp_basis_bp"] = (px["PERP"] / px["INDEX"] - 1) * 1e4
    f["funding_8h"] = fund["funding_8h"]
    f["funding_ann"] = fund["funding_ann"]
    f["funding_ann_7d"] = fund["funding_ann_7d"]

    for t in tags:
        d = np.maximum(dte[t], 1)
        f[f"basis_ann_{t}"] = (px[t] / px["INDEX"] - 1) * (365.0 / d)
        f[f"qbasis_{t}"] = px[t] - px["PERP"]
        f[f"fair_qbasis_{t}"] = px["INDEX"] * f["funding_ann_7d"] * (d / 365.0)
        f[f"gap_{t}"] = f[f"qbasis_{t}"] - f[f"fair_qbasis_{t}"]
        f[f"carry_gap_ann_{t}"] = f[f"basis_ann_{t}"] - f["funding_ann_7d"]

    # curve-fit fair value across [index @ tiny T, whichever dated futures exist]
    Tmat = pd.DataFrame({t: np.maximum(dte[t], 1) / 365.0 for t in tags}, index=px.index)
    imp_carry, fit_r2 = [], []
    for d in px.index:
        avail = [t for t in tags if np.isfinite(px.loc[d, t])]
        if len(avail) < 2:
            imp_carry.append(np.nan); fit_r2.append(np.nan); continue
        prices = pd.Series([px.loc[d, "INDEX"]] + [px.loc[d, t] for t in avail])
        tenors = pd.Series([1 / 365.0] + [Tmat.loc[d, t] for t in avail])
        _, c, r2, _ = fit_carry_curve(prices, tenors)
        imp_carry.append(c); fit_r2.append(r2)
    f["implied_carry"] = imp_carry
    f["fit_r2"] = fit_r2
    f["carry_vs_funding"] = f["implied_carry"] - f["funding_ann_7d"]

    # ---------- deviation (point-in-time z) ----------
    for t in tags:
        f[f"z_gap_{t}"] = pit_z(f[f"gap_{t}"], ROLL_WIN, MIN_OBS)
        f[f"z_basis_{t}"] = pit_z(f[f"basis_ann_{t}"], ROLL_WIN, MIN_OBS)
    f["z_funding"] = pit_z(f["funding_ann_7d"], ROLL_WIN, MIN_OBS)
    f["z_carry_vs_funding"] = pit_z(f["carry_vs_funding"], ROLL_WIN, MIN_OBS)

    # ---------- regime ----------
    ret = np.log(f["index"]).diff()
    rv = ret.rolling(20).std() * np.sqrt(365)
    rv_pct = rv.rolling(120, min_periods=30).apply(lambda w: (w.iloc[-1] >= w).mean())
    f["realised_vol"] = rv
    f["regime_vol"] = np.select([rv_pct < 0.34, rv_pct < 0.67], ["calm", "normal"], "stressed")
    f.loc[rv_pct.isna(), "regime_vol"] = "normal"
    f["regime_funding"] = np.select(
        [f["funding_ann_7d"] > 0.10, f["funding_ann_7d"] < -0.02],
        ["hot", "negative"], "neutral")
    f["ret_20d"] = f["index"] / f["index"].shift(20) - 1
    f["regime_trend"] = np.select([f["ret_20d"] > 0.05, f["ret_20d"] < -0.05], ["up", "down"], "range")

    f.to_csv(clean / "features.csv")

    # curve_long for the dashboard
    rows = []
    for d in px.index:
        rows.append({"date": d, "contract": "PERP", "T": round(1 / 365, 5),
                     "days_to_expiry": 1, "close": px.loc[d, "PERP"], "index": px.loc[d, "INDEX"]})
        for t in tags:
            if not np.isfinite(px.loc[d, t]):
                continue
            rows.append({"date": d, "contract": t, "T": round(Tmat.loc[d, t], 5),
                         "days_to_expiry": int(max(dte_df.loc[d, t], 1)),
                         "close": px.loc[d, t], "index": px.loc[d, "INDEX"]})
    pd.DataFrame(rows).to_csv(clean / "curve_long.csv", index=False)

    # ---------- signals ----------
    sig_rows = []
    for t in tags:
        for d in f.index:
            gap = f.loc[d, f"gap_{t}"]
            z = f.loc[d, f"z_gap_{t}"]
            cg = f.loc[d, f"carry_gap_ann_{t}"]
            ndte = int(max(dte_df.loc[d, t], 1))
            if not np.isfinite(gap) or not np.isfinite(z) or not np.isfinite(px.loc[d, t]):
                continue
            direction = int(-np.sign(gap))          # +1 long qbasis, -1 short qbasis
            idx_px = f.loc[d, "index"]
            notion = idx_px                          # 1 unit of underlying per lot
            fee = FEE_RATE * notion * 4              # 2 legs * in+out
            exp_conv_usd = 0.5 * abs(gap)            # expect half the gap to close
            fund_carry_day = -direction * f.loc[d, "funding_ann_7d"] / 365.0 * notion
            exp_hold = min(MAX_HOLD, max(ndte, 5))
            exp_net = exp_conv_usd + fund_carry_day * exp_hold - fee
            rv_reg = f.loc[d, "regime_vol"]
            regime_mult = 0.55 if rv_reg == "stressed" else 1.0
            adj_net = exp_net * regime_mult
            score = 100 * np.clip(
                0.4 * min(abs(z) / 3, 1) + 0.3 * (adj_net > 0)
                + 0.2 * min(abs(cg) / 0.15, 1) + 0.1 * (ndte >= 20), 0, 1)
            cand = bool(abs(z) >= Z_ENTER and adj_net > 0 and ndte >= 12 and score >= 45)
            sig_rows.append({
                "date": d, "spread": f"qbasis_{t}", "actual": round(f.loc[d, f"qbasis_{t}"], 2),
                "fair": round(f.loc[d, f"fair_qbasis_{t}"], 2), "fair_gap": round(gap, 2),
                "z_fair": round(z, 3), "z_hist": round(f.loc[d, f"z_basis_{t}"], 3)
                if np.isfinite(f.loc[d, f"z_basis_{t}"]) else np.nan,
                "carry_gap_ann": round(cg, 4), "direction": direction,
                "regime_vol": rv_reg, "regime_funding": f.loc[d, "regime_funding"],
                "fee_usd": round(fee, 2), "exp_net_pts": round(exp_net, 2),
                "adj_net_pts": round(adj_net, 2), "near_dte": ndte,
                "signal_score": round(score, 1), "trade_candidate": cand,
            })
    sig = pd.DataFrame(sig_rows).sort_values(["date", "signal_score"], ascending=[True, False])
    sig.to_csv(clean / "signals.csv", index=False)

    # ---------- backtest: HARVEST (always) vs GATED (z-score filtered) ----------
    dates_l = list(px.index)
    tr_h, eq_h = backtest(f, sig, tags, dte_df, dates_l, mode="harvest")
    tr_g, eq_g = backtest(f, sig, tags, dte_df, dates_l, mode="gated")
    tr_h.to_csv(out / "bt_trades_harvest.csv", index=False)
    tr_g.to_csv(out / "bt_trades_gated.csv", index=False)
    pd.concat([eq_h["equity"].rename("equity_harvest"),
               eq_g["equity"].rename("equity_gated")], axis=1).to_csv(out / "bt_equity.csv")
    m_h = {"mode": "harvest (all positive-carry)", **bt_metrics(tr_h, eq_h)}
    m_g = {"mode": "gated (|z_gap|>=1.25 + score)", **bt_metrics(tr_g, eq_g)}
    pd.DataFrame([m_h, m_g]).to_csv(out / "bt_metrics.csv", index=False)
    m = m_g          # the engine's own strategy, used in the summary block

    # ---------- print summary ----------
    last = f.iloc[-1]
    print(f"\n{'='*64}\n{ccy}  —  as of {f.index.max().date()}   ({len(f)} days, curve tags {tags})\n{'='*64}")
    print(f"index                 {last['index']:.1f}")
    print(f"perp basis            {last['perp_basis_bp']:+.1f} bp")
    print(f"funding (7d ann)      {last['funding_ann_7d']*100:+.2f}%   regime: {last['regime_funding']}")
    print(f"curve-implied carry   {last['implied_carry']*100:+.2f}%   fit R^2 {last['fit_r2']:.4f}")
    print(f"carry vs funding      {last['carry_vs_funding']*100:+.2f}%  (z {last['z_carry_vs_funding']:+.2f})")
    print(f"vol regime            {last['regime_vol']} / {last['regime_trend']}\n")
    print("dated future vs funding-fair value:")
    for t in tags:
        print(f"  {t}: qbasis ${last[f'qbasis_{t}']:+8.1f}  fair ${last[f'fair_qbasis_{t}']:+8.1f}  "
              f"gap ${last[f'gap_{t}']:+7.1f}  z {last[f'z_gap_{t}']:+5.2f}  "
              f"carry_gap {last[f'carry_gap_ann_{t}']*100:+.2f}%")
    cand_today = sig[(sig.date == sig.date.max()) & sig.trade_candidate]
    print(f"\ntrade candidates today: {len(cand_today)}")
    for _, r in cand_today.iterrows():
        side = "LONG" if r.direction > 0 else "SHORT"
        print(f"  {side} {r.spread}  z {r.z_fair}  score {r.signal_score}  exp net ${r.adj_net_pts}")
    print(f"\nBACKTEST — harvest (always) vs gated (z-filtered), {ccy}:")
    hdr = ["mode", "n_trades", "win_rate", "total_pnl_usd", "profit_factor",
           "sharpe_ann", "max_dd_usd", "return_on_50k_pct"]
    for row in (m_h, m_g):
        print("  " + " | ".join(f"{k}={row.get(k)}" for k in hdr))
    print("  (does the z-score filter improve on blindly harvesting every contango basis?)")
    print(f"\nwrote {clean}/*.csv  and  {out}/bt_*.csv")


def backtest(f, sig, tags, dte_df, dates, mode="gated"):
    """
    mode='gated'   -> enter only on sig.trade_candidate (z-score + score + cost gate)
    mode='harvest' -> enter on EVERY positive-carry contract with dte>=12, no z filter
                      (the naive 'always short the contango basis' baseline)
    """
    zcol = {t: f[f"z_gap_{t}"] for t in tags}
    open_pos, trades, realised, eq_rows = [], [], 0.0, []
    for d in dates:
        still = []
        for p in open_pos:
            t = p["tag"]; gap_now = f.loc[d, f"gap_{t}"]
            z_now = zcol[t].get(d, np.nan)
            held = (d - p["entry_date"]).days
            fund_day = -p["dir"] * f.loc[d, "funding_ann_7d"] / 365.0 * p["notion"]
            p["fund_accum"] = p.get("fund_accum", 0.0) + fund_day
            mtm = p["dir"] * (gap_now - p["entry_gap"]) + p["fund_accum"]
            reason = None
            if not np.isfinite(gap_now):
                reason = "no_price"
            elif np.isfinite(z_now) and abs(z_now) < 0.4:
                reason = "reverted"
            elif held >= MAX_HOLD:
                reason = "max_hold"
            elif mtm <= -STOP_FRAC * abs(p["entry_gap"]) - p["fee"]:
                reason = "stop"
            elif int(max(dte_df.loc[d, t], 1)) <= 8:
                reason = "expiry"
            if reason:
                pnl = p["dir"] * (gap_now - p["entry_gap"]) + p["fund_accum"] - p["fee"]
                realised += pnl * POINT
                trades.append({"tag": t, "entry_date": p["entry_date"], "exit_date": d,
                               "held_days": held, "dir": p["dir"],
                               "entry_gap": round(p["entry_gap"], 1), "exit_gap": round(gap_now, 1),
                               "funding_pnl": round(p["fund_accum"], 1), "fee": round(p["fee"], 1),
                               "pnl_usd": round(pnl, 1), "exit_reason": reason,
                               "regime_vol": p["regime_vol"]})
            else:
                still.append(p)
        open_pos = still
        held_tags = {p["tag"] for p in open_pos}
        day = sig[sig.date == d]
        if mode == "gated":
            todays = day[day.trade_candidate]
        else:   # harvest: any positive-carry contract with enough time left
            todays = day[(day.carry_gap_ann > 0) & (day.near_dte >= 12)]
        todays = todays.sort_values("signal_score", ascending=False)
        for _, r in todays.iterrows():
            if len(open_pos) >= 3:
                break
            t = r["spread"].split("_")[1]
            if t in held_tags:
                continue
            open_pos.append({
                "tag": t, "entry_date": d, "entry_gap": float(f.loc[d, f"gap_{t}"]),
                "dir": int(r["direction"]), "notion": float(f.loc[d, "index"]),
                "fee": float(r["fee_usd"]), "regime_vol": r["regime_vol"],
            })
            held_tags.add(t)
        open_mtm = sum(p["dir"] * (f.loc[d, f"gap_{p['tag']}"] - p["entry_gap"]) + p.get("fund_accum", 0.0)
                       for p in open_pos)
        eq_rows.append({"date": d, "realised": realised, "equity": realised + open_mtm,
                        "n_open": len(open_pos)})
    return pd.DataFrame(trades), pd.DataFrame(eq_rows).set_index("date")


def bt_metrics(tr, eq):
    if tr.empty:
        return {"n_trades": 0}
    wins = tr[tr.pnl_usd > 0]["pnl_usd"]; losses = tr[tr.pnl_usd <= 0]["pnl_usd"]
    dr = eq["equity"].diff().dropna() / NOTIONAL
    sharpe = dr.mean() / dr.std() * np.sqrt(365) if dr.std() > 0 else np.nan
    dd = (eq["equity"] - eq["equity"].cummax()).min()
    return {"n_trades": len(tr), "win_rate": round((tr.pnl_usd > 0).mean(), 3),
            "total_pnl_usd": round(tr.pnl_usd.sum(), 0),
            "avg_win": round(wins.mean(), 1) if len(wins) else 0.0,
            "avg_loss": round(losses.mean(), 1) if len(losses) else 0.0,
            "profit_factor": (round(wins.sum() / abs(losses.sum()), 2)
                              if losses.sum() != 0 else float("inf")),
            "n_losses": int((tr.pnl_usd <= 0).sum()),
            "avg_hold_days": round(tr.held_days.mean(), 1),
            "sharpe_ann": round(sharpe, 2), "max_dd_usd": round(dd, 0),
            "return_on_50k_pct": round(tr.pnl_usd.sum() / NOTIONAL * 100, 2)}


if __name__ == "__main__":
    build((sys.argv[1] if len(sys.argv) > 1 else "BTC").upper())
