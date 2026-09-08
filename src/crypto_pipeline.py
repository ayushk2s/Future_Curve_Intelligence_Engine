"""
CRYPTO PIPELINE — fetch + analyse BTC and ETH (Deribit, no API key).

  python src/crypto_pipeline.py               fetch fresh, then analyse
  python src/crypto_pipeline.py --skip-fetch  reuse data/crypto/<CCY>/raw/
"""

import sys
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
FETCH = HERE / "crypto" / "fetch_crypto.py"
ENGINE = HERE / "crypto" / "engine.py"
CCYS = ["BTC", "ETH"]


def run(script: pathlib.Path, *args: str) -> None:
    print(f"\n{'='*66}\n# {script.name} {' '.join(args)}\n{'='*66}")
    subprocess.run([sys.executable, str(script), *args], check=True)


def main() -> None:
    skip = "--skip-fetch" in sys.argv
    for ccy in CCYS:
        if not skip:
            run(FETCH, ccy)
        run(ENGINE, ccy)
    print("\nall crypto markets done.  streamlit run app/dashboard.py  (pick market in sidebar)")


if __name__ == "__main__":
    main()
