# Architecture

## Design goals

1. **Point-in-time everywhere.** Any number available on day *t* uses only data from *t* or earlier. Rolling stats are lagged (`.rolling(N).mean().shift(1)`); ML models are retrained walk-forward; fair value uses only that day's cross-section.
2. **Raw data is immutable.** `data/raw/` is written once and never edited. Every downstream stage reads it and writes *new* files, so a bug in feature code cannot corrupt the source and any backtest is reproducible from identical bytes.
3. **Instrument-agnostic core.** The gold and crypto engines share the same clean-CSV schema and the same statistical primitives (`fit_carry_curve`, `pit_z`). Adding a market is a data adapter + contract rules.
4. **Honesty over performance.** The engine is built to say "stand aside" when there is no edge, and the backtest compares against naive baselines to show what each discipline layer is worth.

## Data flow

```
                    ┌──────────────┐
   Yahoo / Deribit ─┤ fetch_*      │─▶ data/raw/*.csv            (immutable)
                    └──────────────┘
                           │
                    ┌──────────────┐
                    │ curve.py     │─▶ curve_long.csv            clean date×contract panel + T
                    └──────────────┘
                           │
             ┌─────────────┼──────────────┐
     ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
     │ features.py   │ │ fairvalue.py │ │ regime.py    │
     │ basis,spreads │ │ carry fit    │ │ vol/trend    │
     │ slope,curv    │ │ implied c,R² │ │ regimes      │
     └───────────────┘ └──────────────┘ └──────────────┘
             │                │                │
             └────────┬───────┴────────┬───────┘
              ┌──────────────┐  ┌──────────────┐
              │ deviation.py │  │ convergence  │
              │ z_hist,z_fair│  │ half-life,   │
              │ anomalies    │  │ reversion tbl│
              └──────────────┘  └──────────────┘
                     │                │
              ┌──────────────┐        │
              │ predict.py   │        │
              │ OU/Ridge/GBR │        │
              │ walk-forward │        │
              └──────────────┘        │
                     │                │
              ┌───────────────────────────────┐
              │ signals.py                    │
              │ fair-gap → direction          │
              │ → cost/regime/model gate      │
              │ → 0–100 score → candidate     │
              └───────────────────────────────┘
                     │
              ┌──────────────┐
              │ backtest.py  │─▶ data/output/bt_*   equity curves + metrics
              └──────────────┘
                     │
        ┌────────────┴────────────┐
  ┌──────────────┐        ┌──────────────┐
  │ dashboard.py │        │ monitor.py   │─▶ alerts.json
  └──────────────┘        └──────────────┘
```

## Key decisions

| Decision | Why |
|----------|-----|
| Nearest contract as gold "spot" anchor | No free cash-gold feed (`XAUUSD=X` delisted, stooq bot-walled). By convergence, the nearest future *is* a spot proxy; all features are inter-contract anyway. |
| Log-linear carry fit (`ln F = a + c·T`) | Matches the continuous cost-of-carry form `F = S·e^{cT}`; one OLS per day gives the implied carry rate and fair curve. Gold R² ≈ 0.999. |
| `z_fair` alongside `z_hist` | A rolling mean is a stale benchmark: when rates genuinely rise, `z_hist` flags a false anomaly while `z_fair` (vs the live carry curve) stays calm. Worked example in the explainer. |
| Drop `slope_ann` from ML features | It is ≈ the sum of the calendar spreads — collinear, not extra information. |
| GBR only as a weak tilt | With ~240 days, OU and Ridge showed no out-of-sample skill; GBR hit 0.54 / corr 0.19. Treated as a nudge, gated on agreement. |
| Crypto tradeable = `qbasis` (dated − perp) vs `index × funding_ann_7d × T` | Funding is the crypto carry rate; the gap between the quarterly premium and what funding implies is the real dislocation. |
| Harvest vs gated backtest for crypto | Proves the z-score filter (not roll-down) is the edge: blind harvesting loses, gated is positive. |
| Walk-forward, expanding window, retrain every 20 days | The honest way to score a time-series model; a random split leaks the future. |

## Point-in-time / no-look-ahead guarantees

- `deviation.pit_z` = `(x − rolling_mean.shift(1)) / rolling_std.shift(1)` — the stats never see the current row. Unit-tested (`test_pit_z_has_no_look_ahead`, `test_pit_z_is_lagged`).
- `predict.walk_forward` trains only on `date < d` with a resolved target, then predicts `d`.
- `fairvalue.fit_carry_curve` uses only the current day's prices.
- `backtest` iterates dates forward; entries use that day's signal row, exits use that day's marks, costs are charged on exit.

## Extending to a new market (e.g. Silver, NIFTY)

1. Write a fetch adapter that outputs the same `data/raw/<sym>.csv` schema (`date,open,high,low,close,volume`).
2. Add the contract's root symbol, month-code map and expiry rule to `contracts.py` (month codes F–Z are already universal).
3. If the instrument has a funding rate (perps) or dividend yield (index), add it as a feature and a carry term in the fair-value fit.
4. Everything downstream — deviation, regime, convergence, signals, backtest, dashboard — is unchanged.

## Tech

Python 3.9+, pandas / numpy / scikit-learn, Streamlit + Plotly for the UI. No API keys required (Yahoo Finance + Deribit public endpoints). Full gold pipeline runs in ~3 s; crypto (BTC+ETH) in ~5 s after data is cached.
