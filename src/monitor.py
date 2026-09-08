"""
LIVE MONITOR / DEVIATION ALERTS  (blueprint section 22 - "notify about deviation")

Refreshes data, re-runs the pipeline, and emits alerts for the latest date:

  * any spread with |z_fair| >= Z_ALERT          -> "deviation" alert
  * any signals.trade_candidate == True          -> "candidate" alert
  * curve state flip (contango <-> backwardation) -> "regime" alert

Writes data/output/alerts.json and prints a human-readable digest. Wire the
JSON to email / Slack / Telegram in deploy (a send_* stub is included).

Usage:
  python src/monitor.py                 refresh + evaluate
  python src/monitor.py --no-refresh    evaluate current CSVs only
"""

import json
import pathlib
import sys
import datetime as dt

import pandas as pd

from _paths import CLEAN_DIR as CLEAN, OUT_DIR as OUT

Z_ALERT = 1.5


def refresh() -> None:
    import pipeline
    sys.argv = ["pipeline.py", "--refetch"]
    pipeline.main()


def evaluate() -> dict:
    sig = pd.read_csv(CLEAN / "signals.csv", parse_dates=["date"])
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    fv = pd.read_csv(CLEAN / "fairvalue.csv", parse_dates=["date"]).set_index("date")
    reg = pd.read_csv(CLEAN / "regime.csv", parse_dates=["date"]).set_index("date")

    d = sig["date"].max()
    today = sig[sig["date"] == d].copy()
    alerts = []

    for _, r in today.iterrows():
        if pd.notna(r["z_fair"]) and abs(r["z_fair"]) >= Z_ALERT:
            alerts.append({
                "type": "deviation", "spread": r["spread"],
                "z_fair": round(float(r["z_fair"]), 2),
                "fair_gap_pts": round(float(r["fair_gap"]), 2),
                "msg": f"{r['spread']} sits {r['z_fair']:+.2f}σ from its carry-fair value "
                       f"({r['fair_gap']:+.2f} pts)",
            })
        if bool(r["trade_candidate"]):
            side = "LONG" if r["direction"] > 0 else "SHORT"
            alerts.append({
                "type": "candidate", "spread": r["spread"], "side": side,
                "score": float(r["signal_score"]),
                "exp_net_usd": round(float(r["adj_net_pts"]) * 100, 0),
                "msg": f"TRADE CANDIDATE: {side} {r['spread']} | score {r['signal_score']} "
                       f"| exp net ${r['adj_net_pts']*100:.0f}/lot | regime {r['regime_vol']}",
            })

    # curve-state flip
    cs = feats["cs_Z_V"]
    state_now = "contango" if cs.iloc[-1] > 0 else "backwardation"
    state_prev = "contango" if cs.iloc[-2] > 0 else "backwardation"
    if state_now != state_prev:
        alerts.append({"type": "regime",
                       "msg": f"curve state flipped {state_prev} -> {state_now}"})

    digest = {
        "as_of": str(d.date()),
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "curve_state": state_now,
        "implied_carry_pct": round(float(fv["implied_carry"].iloc[-1]) * 100, 2),
        "regime": f"{reg['regime_vol'].iloc[-1]}/{reg['regime_trend'].iloc[-1]}",
        "n_alerts": len(alerts),
        "alerts": alerts,
    }
    return digest


def send_notification(digest: dict) -> None:
    """Deploy stub -- replace with real email/Slack/Telegram push."""
    # e.g. requests.post(SLACK_WEBHOOK, json={"text": render(digest)})
    pass


def main() -> None:
    if "--no-refresh" not in sys.argv:
        refresh()
    digest = evaluate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "alerts.json").write_text(json.dumps(digest, indent=2))

    print("\n" + "=" * 60)
    print(f"MONITOR DIGEST  as of {digest['as_of']}")
    print("=" * 60)
    print(f"curve state     : {digest['curve_state']}")
    print(f"implied carry   : {digest['implied_carry_pct']}% /yr")
    print(f"regime          : {digest['regime']}")
    print(f"alerts          : {digest['n_alerts']}")
    for a in digest["alerts"]:
        print(f"  [{a['type']:9s}] {a['msg']}")
    if not digest["alerts"]:
        print("  (nothing abnormal — engine says stand aside)")
    print(f"\nwrote {OUT / 'alerts.json'}")
    send_notification(digest)


if __name__ == "__main__":
    main()
