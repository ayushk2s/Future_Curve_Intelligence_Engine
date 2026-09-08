"""
END-TO-END PIPELINE  (blueprint section 6)

Runs every stage in dependency order:

  fetch -> curve -> features -> fairvalue -> deviation -> regime
        -> convergence -> predict -> signals -> backtest

Usage:
  python src/pipeline.py                 full run (re-downloads if raw missing)
  python src/pipeline.py --skip-fetch    reuse data/raw/*.csv
  python src/pipeline.py --refetch       force re-download
"""

import sys
import time

import fetch_data
import curve
import features
import fairvalue
import deviation
import regime
import convergence
import predict
import signals
import backtest


STEPS = [
    ("fetch", None),          # handled specially
    ("curve", curve.build),
    ("features", features.build),
    ("fairvalue", fairvalue.build),
    ("deviation", deviation.build),
    ("regime", regime.build),
    ("convergence", convergence.build),
    ("predict", predict.build),
    ("signals", signals.build),
    ("backtest", backtest.main),
]


def main() -> None:
    skip_fetch = "--skip-fetch" in sys.argv
    refetch = "--refetch" in sys.argv

    t0 = time.time()
    for name, fn in STEPS:
        print(f"\n{'='*70}\n# {name.upper()}\n{'='*70}")
        ts = time.time()
        if name == "fetch":
            if skip_fetch:
                print("  skipped (using cached data/raw/)")
                continue
            if refetch:
                sys.argv.append("--force")
            fetch_data.main()
        else:
            fn()
        print(f"  [{name} done in {time.time()-ts:.1f}s]")

    print(f"\n{'='*70}\nPIPELINE COMPLETE in {time.time()-t0:.1f}s")
    print("outputs: data/clean/*.csv  data/output/*.csv")
    print("next:    streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
