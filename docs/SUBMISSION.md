# Futures Curve Intelligence Engine — Submission

## Inspiration

Every futures market carries a *curve* — the price of the same asset at different maturities — and that curve is a compressed statement of what the market charges to hold the asset through time: financing, storage, dividends, scarcity, and, for crypto, the perpetual funding rate. Most retail "signals" traded off that curve are noise: two contracts being *close* is not an opportunity. I wanted to build the thing that actually answers the hard question — *given maturity, carry, regime, liquidity and history, is today's curve materially mispriced, and does the edge survive costs?* — and to build it so it tells the truth when the answer is "no".

## What it does

A single pipeline, applied to three markets (Gold on COMEX, BTC and ETH on Deribit):

1. **Reconstructs the curve** from raw contract data with point-in-time cleaning.
2. **Prices it from first principles** — a cost-of-carry fair value fitted daily (`ln F = a + c·T`), giving an implied carry rate. Gold's curve fits this to R² ≈ 0.999.
3. **Measures disagreement two ways** — deviation vs the spread's own history (`z_hist`) and deviation vs the carry curve (`z_fair`). The second is the real signal; the first catches false alarms when rates genuinely move.
4. **Conditions on regime** — calm / normal / stressed, trending / range, and for crypto a funding regime — because mean-reversion that works in calm markets breaks in stressed ones.
5. **Forecasts** the next 10-day spread move with a walk-forward Gradient-Boosting model (used as a weak tilt — it is honest about ~54% hit rate on one year of data).
6. **Filters for tradability** — a tick-size / fee cost model, liquidity tiers, days-to-expiry, model agreement — and only then emits a *trade candidate* with a 0–100 score.
7. **Backtests** everything walk-forward with realistic costs, against naive baselines, and reports the full metric set.
8. **Ships a product** — a Streamlit dashboard with a market selector and a deviation-alert monitor.

## How I built it

- **Data**: Yahoo Finance for gold contracts; Deribit's public API for BTC/ETH perpetual + dated futures + index + funding-rate history. No API keys.
- **Core**: Python, pandas/numpy, scikit-learn. The gold and crypto engines share the same clean-CSV schema and the same statistical primitives, so a new market is a data adapter plus contract rules.
- **Discipline**: every rolling statistic is lagged, every model is retrained walk-forward, and a unit test asserts the no-look-ahead property directly.
- **UI**: Streamlit + Plotly.

## Results

Walk-forward backtest, per $50k book, ~1 year, in-sample.

**Gold** — the engine says *stand aside* (efficient curve). It proves the discipline matters: naive z-score fading loses −$4,140 (profit factor 0.19); the fully-gated strategy contains it to −$580 (0.60) while trading 60% less. Naive loses ~7× the disciplined version.

**BTC** — a real, modest funding-basis edge: the gated strategy makes +$7,058 (+14% / $50k, Sharpe 0.84, profit factor 1.68, max drawdown −$7,115) over 29 trades. The "harvest every contango basis" baseline *loses* −$8,844 — so the z-score filter, not the roll-down, is the edge.

**ETH** — the curve sits within ~0.5% of funding-fair value, so even the gated strategy is near flat (+$349). The engine correctly issues few candidates. It does not manufacture trades.

## Challenges

- **No free spot-gold feed.** `XAUUSD=X` is delisted on Yahoo and stooq now serves a JS bot-wall. Resolved by anchoring on the nearest contract (which converges to spot anyway) and computing every feature inter-contract.
- **Small samples.** 241 trading days for gold, ~400 for crypto (one funding regime). I leaned on simple, regularised models and am explicit that the Sharpe figures are not statistically significant.
- **A false-positive trap.** Early on, `z_hist` flagged every gold calendar spread as "1.3σ wide". The carry fit showed the *rate itself* had risen — the steepness was real, not a mispricing. That failure is why `z_fair` exists.
- **Overtrading.** The first crypto backtest harvested every basis and looked great on 74 days; extending to 400 days and adding the harvest-vs-gated comparison showed blind harvesting actually loses.

## What I learned

- A statistical deviation is an *investigation signal*, never a trade. Gold's calendar spreads had `p_revert < 0.5` in every z bucket — they trended, they didn't revert. Measuring that beats assuming mean reversion.
- The most valuable output of a quant engine is often "no trade". An engine that curve-fits a fake winner is worse than one that correctly abstains.
- Cost modelling is not a footnote. On gold, round-trip cost (~1.1 pts) is a quarter of a spread's standard deviation; on crypto, overtrading a thin edge turns +$15k gross into −$9k net.

## What's next

- **More history & regimes** — MCX bhavcopy for gold, multiple years of crypto funding cycles, to put confidence intervals on the edge.
- **More markets** — Silver (storage dynamics), NIFTY / BANKNIFTY (dividend carry), using the existing adapter interface.
- **PCA factor model** — the data already shows one factor drives all of gold's calendar spreads.
- **Probability calibration** on the convergence study, and score-scaled position sizing.
- **Paper trading** wired to the monitor, alerts to Slack / Telegram.

## Try it

```bash
pip install -r requirements.txt
python demo.py                              # gold + crypto, prints the results table
python -m streamlit run app/dashboard.py    # interactive dashboard
```

Full term-by-term explainer with the profitability analysis: **docs/EXPLAINER.pdf**.

---
*Research / decision-support only. Not investment advice. All figures are in-sample and unvalidated. Trading futures carries substantial risk of loss.*
