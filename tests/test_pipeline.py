"""
Test suite — invariants that must hold for the engine to be trustworthy.

  python -m pytest -q tests/

Pure-unit tests (no data) always run. Integration checks run only if the
pipelines have been executed (data/ populated); otherwise they skip.
"""

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deviation import pit_z                       # noqa: E402
from fairvalue import fit_carry_curve             # noqa: E402
from contracts import parse_comex_gold           # noqa: E402


# --------------------------------------------------------------- pure unit
def test_contract_parser():
    c = parse_comex_gold("GCZ26.CMX")
    assert c.underlying == "GOLD"
    assert c.contract_month == "December"
    assert c.year == 2026
    assert c.expiry.month == 12


def test_carry_fit_recovers_a_known_rate():
    S, rate = 2500.0, 0.05
    T = pd.Series([0.1, 0.25, 0.5, 0.75, 1.0])
    F = pd.Series(S * np.exp(rate * T))
    spot, c, r2, fair = fit_carry_curve(F, T)
    assert abs(c - rate) < 1e-6
    assert r2 > 0.999999
    assert np.allclose(fair, F.values, rtol=1e-6)


def test_pit_z_has_no_look_ahead():
    """z at time t must be identical whether or not future data exists."""
    rng = np.random.default_rng(0)
    s = pd.Series(np.cumsum(rng.normal(size=300)))
    z_full = pit_z(s)
    cut = 200
    z_trunc = pit_z(s.iloc[:cut])
    # values up to the cut must match exactly (future rows can't have changed them)
    a = z_full.iloc[:cut].dropna()
    b = z_trunc.reindex(a.index)
    assert np.allclose(a.values, b.values, equal_nan=True)


def test_pit_z_is_lagged():
    """z at t must not use the rolling stats that include t itself."""
    s = pd.Series(np.arange(100.0))
    z = pit_z(s, win=20, min_obs=20)
    # first 20 rows can't have a value (need 20 priors + the shift)
    assert z.iloc[:20].isna().all()
    assert z.notna().iloc[21:].all()


# --------------------------------------------------------------- integration
GOLD = ROOT / "data/clean"
OUT = ROOT / "data/output"
needs_gold = pytest.mark.skipif(not (GOLD / "signals.csv").exists(),
                                reason="run `python src/pipeline.py` first")
needs_crypto = pytest.mark.skipif(not (ROOT / "data/crypto/BTC/clean/features.csv").exists(),
                                  reason="run `python src/crypto_pipeline.py` first")


@needs_gold
def test_gold_outputs_present_and_shaped():
    for name in ["curve_long", "features", "fairvalue", "deviation", "regime",
                 "convergence", "predictions", "signals"]:
        assert (GOLD / f"{name}.csv").exists(), name
    sig = pd.read_csv(GOLD / "signals.csv")
    assert {"z_fair", "adj_net_pts", "trade_candidate", "signal_score"} <= set(sig.columns)
    assert sig["signal_score"].between(0, 100).all()


@needs_gold
def test_gold_trade_candidates_have_positive_expected_edge():
    sig = pd.read_csv(GOLD / "signals.csv")
    cand = sig[sig["trade_candidate"]]
    assert (cand["exp_net_pts"] > 0).all()
    assert (cand["z_fair"].abs() >= 1.25).all()


@needs_gold
def test_carry_fit_is_good():
    fv = pd.read_csv(GOLD / "fairvalue.csv")
    assert fv["fit_r2"].mean() > 0.99


@needs_gold
def test_convergence_probabilities_are_valid():
    c = pd.read_csv(GOLD / "convergence.csv")
    assert c["p_revert"].between(0, 1).all()


@needs_gold
def test_backtest_metrics_sane():
    m = pd.read_csv(OUT / "bt_metrics.csv")
    assert m["win_rate"].between(0, 1).all()
    assert (m["n_trades"] > 0).all()


@needs_crypto
def test_crypto_schema_and_harvest_vs_gated():
    for ccy in ["BTC", "ETH"]:
        f = pd.read_csv(ROOT / f"data/crypto/{ccy}/clean/features.csv")
        assert any(c.startswith("qbasis_") for c in f.columns)
        assert any(c.startswith("z_gap_") for c in f.columns)
        m = pd.read_csv(ROOT / f"data/crypto/{ccy}/output/bt_metrics.csv")
        assert set(m["mode"].str.split().str[0]) == {"harvest", "gated"}
