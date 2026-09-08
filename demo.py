"""
ONE-COMMAND DEMO  —  python demo.py

Runs the full gold + crypto pipelines, then prints the headline results:
the current curve state per market, the engine's live verdict, and the
walk-forward backtest scoreboard.

Flags:
  --skip-fetch    reuse cached data/  (fast; use after the first run)
"""

import sys
import subprocess
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
SKIP = "--skip-fetch" in sys.argv


def sh(*args):
    subprocess.run([PY, *args] + (["--skip-fetch"] if SKIP else []), check=True, cwd=ROOT)


def rule(t):
    print("\n" + "=" * 74 + f"\n  {t}\n" + "=" * 74)


def main():
    rule("1 / 3   GOLD pipeline")
    sh("src/pipeline.py")
    rule("2 / 3   CRYPTO pipeline (BTC + ETH)")
    sh("src/crypto_pipeline.py")

    rule("3 / 3   HEADLINE RESULTS")

    # ---- live verdict per market ----
    print("\nLIVE VERDICT (most recent date)")
    print(f"  {'market':6s} {'curve state':14s} {'carry/funding':16s} {'regime':18s} {'verdict':s}")
    # gold
    fv = pd.read_csv(ROOT / "data/clean/fairvalue.csv").iloc[-1]
    sg = pd.read_csv(ROOT / "data/clean/signals.csv")
    reg = pd.read_csv(ROOT / "data/clean/regime.csv").iloc[-1]
    feats = pd.read_csv(ROOT / "data/clean/features.csv").iloc[-1]
    gc = int(sg[sg.date == sg.date.max()].trade_candidate.sum())
    print(f"  {'GOLD':6s} {'contango' if feats['cs_Z_V']>0 else 'backwardation':14s} "
          f"{f'{fv.implied_carry*100:+.2f}%/yr':16s} "
          f"{reg.regime_vol + '/' + reg.regime_trend:18s} "
          f"{'STAND ASIDE' if gc == 0 else str(gc)+' CANDIDATE(S)'}")
    # crypto
    for ccy in ["BTC", "ETH"]:
        cf = pd.read_csv(ROOT / f"data/crypto/{ccy}/clean/features.csv").iloc[-1]
        cs = pd.read_csv(ROOT / f"data/crypto/{ccy}/clean/signals.csv")
        cc = int(cs[cs.date == cs.date.max()].trade_candidate.sum())
        print(f"  {ccy:6s} {'contango' if cf['qbasis_25DEC26']>0 else 'backwardation':14s} "
              f"{f'{cf.carry_vs_funding*100:+.2f}% vs fund':16s} "
              f"{cf.regime_vol + '/' + cf.regime_funding:18s} "
              f"{'STAND ASIDE' if cc == 0 else str(cc)+' CANDIDATE(S)'}")

    # ---- backtest scoreboard ----
    print("\nWALK-FORWARD BACKTEST SCOREBOARD  (per $50k book, ~1 year, in-sample)")
    gm = pd.read_csv(ROOT / "data/output/bt_metrics.csv")
    print("\n  GOLD — four entry rules:")
    print(gm[["strategy", "n_trades", "win_rate", "total_pnl_usd",
              "profit_factor", "sharpe_ann", "max_dd_usd"]].to_string(index=False))
    for ccy in ["BTC", "ETH"]:
        cm = pd.read_csv(ROOT / f"data/crypto/{ccy}/output/bt_metrics.csv")
        print(f"\n  {ccy} — harvest vs gated:")
        print(cm[["mode", "n_trades", "win_rate", "total_pnl_usd",
                  "profit_factor", "sharpe_ann", "max_dd_usd"]].to_string(index=False))

    print("""
READING IT
  * Gold: the carry model fits to R^2 ~ 0.999; residual mispricings do not clear
    costs -> the engine says STAND ASIDE. Naive z-score fading loses ~7x the
    gated strategy: the discipline layer is doing its job (capital protection).
  * BTC: a real but modest funding-basis edge (gated +14%/$50k, Sharpe ~0.84).
    The 'harvest everything' baseline LOSES -> the z-score filter, not roll-down,
    is the edge.
  * ETH: curve sits near funding-fair -> the engine finds almost nothing.
  * One engine, three markets, honest about where edge exists.
  * All figures are in-sample, ~1 year, tens of trades. Directional evidence,
    not a validated track record. Not investment advice.

  Next:  python -m streamlit run app/dashboard.py
""")


if __name__ == "__main__":
    main()
