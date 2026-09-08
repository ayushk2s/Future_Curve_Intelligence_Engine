# Multi-Market Futures Curve Intelligence & Modeling — Blueprint

*The specification this project was built from. Section numbers (§) are referenced throughout the code and docs.*

A beginner-friendly blueprint for building a quantitative futures-curve research, prediction, deviation-detection, backtesting, and trade-opportunity engine.

## 1. Objective

Build one Futures Curve Intelligence Engine covering:

- Crypto: BTC, ETH
- Metals: Gold, Silver
- Indian indexes: NIFTY, BANKNIFTY

The system should reconstruct futures curves, measure basis and calendar spreads, estimate fair value, detect statistically abnormal relationships, predict curve/spread behavior, account for costs and liquidity, backtest signals, and produce trade candidates.

## 2. Core Concept — What Is a Futures Curve?

A futures contract is an agreement for exposure to an underlying asset at a specified future maturity. A futures curve is the relationship between futures prices and their maturities.

Example: Spot Gold = $2,500; 1M = $2,515; 3M = $2,540; 6M = $2,580; 12M = $2,650. Plot maturity on the x-axis and futures price on the y-axis: the resulting relationship is the futures curve.

As expiry approaches, a futures contract generally converges toward the relevant spot/settlement value according to the exchange's rules.

## 3. Why Futures Prices Differ From Spot

Futures prices are influenced by the spot price plus the economics of carrying/exposure through time.

- NIFTY: financing/carry and expected dividends are important.
- BTC/ETH: financing, borrowing/lending conditions, market demand, and crypto-specific futures/perpetual mechanics matter.
- Gold/Silver: financing, storage, insurance, and benefits of holding the physical asset can matter.

Do not assume that futures are simply a prediction of the future spot price.

## 4. Key Terminology

Spot price: The current market price of the underlying. Futures price: The current market price of a futures contract for a particular maturity. Expiry: The date/maturity associated with a futures contract. Convergence: The tendency for futures and the relevant spot/settlement value to come together near expiry. Basis: Futures price minus spot price; often also normalized as a percentage. Carry: The costs and benefits associated with maintaining exposure until a future date. Contango: A curve condition where later-dated futures are generally priced above nearby/spot prices. Backwardation: A curve condition where later-dated futures are generally priced below nearby/spot prices. Calendar spread: The price relationship/difference between futures contracts with different maturities of the same underlying. Z-score: A standardized measure of how far an observation is from its historical mean in standard-deviation units. Fair value: A model-based estimate of what a contract or spread should be worth under the chosen assumptions/model. Curve slope: A measure of how rapidly futures prices change with maturity. Curve curvature: A measure of how the middle of the curve differs from a simple straight-line relationship. Roll yield: The gain/loss associated with replacing an expiring futures position with a later maturity; it depends on the curve and position.

## 5. Markets and Contracts

**BTC / ETH**: Spot · Perpetual · Dated futures · Funding rate · Mark/index prices · Volume/open interest.

**Gold / Silver**: Spot · Front/near futures · Next/far futures · Longer maturities where liquid · Volume/open interest.

**NIFTY / BANKNIFTY**: Spot index · Near futures · Next futures · Far futures · Volume/open interest.

## 6. End-to-End System Pipeline

MARKET DATA → DATA NORMALIZATION → CONTRACT MAPPING → CURVE BUILDER → BASIS/SPREAD/SHAPE FEATURES → FAIR-VALUE MODEL → DEVIATION/Z-SCORE → PREDICTION ENGINE → REGIME DETECTION → COST & LIQUIDITY FILTER → SIGNAL/RISK ENGINE → BACKTEST → LIVE MONITOR/API

## 7. Data Layer

For each observation, store as much as the market provides: timestamp, underlying, contract symbol, expiry, days to expiry, bid, ask, last/mark, OHLC where appropriate, volume, open interest, spot/index price, funding rate for crypto, index/mark price for crypto. Keep raw data immutable and create cleaned/normalized datasets separately.

## 8. Contract Normalization

Convert exchange-specific symbols into a common internal schema. Example: `GOLD26FEB` → underlying=GOLD, expiry=<date>, days_to_expiry=<calculated>, contract_month=February. Do this for every exchange so the modeling layer works with standardized fields.

## 9. Curve Construction

For each timestamp, sort contracts by time to expiry and create a curve. Store both raw contract observations and a maturity-normalized representation so curves from different dates can be compared. Do not blindly compare calendar months; compare contracts with appropriate time-to-expiry and liquidity context.

## 10. Core Curve Features

Basis = Futures − Spot; Basis % = (Futures − Spot) / Spot; pairwise calendar spreads (Mar−Feb, Apr−Mar, …); spread returns and changes; curve slope; curve curvature; term-structure level; roll yield; volume and open-interest structure; bid-ask spread and liquidity measures.

## 11. Pairwise Spread / Deviation Engine

For each pair of maturities, estimate the historical behavior of their spread. Example: if Mar−Feb historically averages 8 with std 3, and today's spread is 1, the raw deviation is −7 and the simple z-score is (1−8)/3 = −2.33.

A large z-score is not automatically a trade. It is an investigation signal. The system must check whether the deviation is explainable by expiry, carry, volatility, liquidity, events, or market regime.

## 12. Fair-Value Curve

Estimate a smooth/theoretical curve or expected spread structure rather than relying only on historical averages. In increasing complexity: simple carry/basis models; linear regression; polynomial or spline curves; Nelson-Siegel-style term-structure models; PCA factor models; Kalman filters/state-space models; machine-learning models; neural networks/transformers only after strong baselines. The first production-quality version should start with simple statistical and carry-aware baselines.

## 13. Curve Factors

Level (the overall curve moves higher/lower); Slope (steeper/flatter); Curvature (middle differs from a straight line). PCA can later discover dominant empirical curve-movement factors.

## 14. Prediction Engine

Define explicit prediction targets: next-period futures return; future futures price / normalized curve value; calendar-spread change; future basis; slope change; curvature change; volatility; probability of spread convergence; expected time to convergence; expected gross and net P&L.

## 15. Feature Set for ML

Spot returns and volatility; futures returns and volatility; basis and basis change; calendar spreads and z-scores; days to expiry; curve slope/curvature/factors; volume and open interest; bid-ask/liquidity; funding rates for BTC/ETH; interest rates/yields where relevant; USD-related variables; cross-asset relationships; regime indicators; event/calendar features.

## 16. Modeling Stack

Baseline: historical mean/median and carry-aware rules. Statistics: linear regression, rolling z-scores, ARIMA/state-space. ML: XGBoost/LightGBM. Volatility: GARCH or similar. State/regime models: hidden-state or clustering. Deep learning: LSTM/temporal models/transformers only after robust baselines and sufficient data.

## 17. Regime Detection

Classify conditions such as normal, high-volatility, stressed, trending, or mean-reverting. A spread that normally mean-reverts may behave very differently during a market shock. Signals should be conditional on regime.

## 18. Trade-Signal Logic

Example workflow for a Feb–Mar Gold relationship: calculate Mar−Feb spread; estimate fair spread using the appropriate maturity/carry/regime model; calculate deviation and standardized deviation; estimate probability of convergence; estimate expected convergence horizon; check volume, open interest, bid-ask spread, slippage, transaction costs; check days to expiry and expiry-specific effects; estimate expected net P&L and downside/risk; only classify as a trade candidate if the edge remains after costs and risk filters.

Key principle: "contracts are close" is NOT itself a signal. The signal is that their relationship is statistically/economically abnormal relative to an appropriate fair-value model.

## 19. Signal Score

A dashboard can combine: deviation magnitude; model confidence; convergence probability; expected net P&L; liquidity; execution cost; risk; days to expiry; regime compatibility. Example output: Signal score 87/100 — a ranking/decision-support score, not a guarantee of profit.

## 20. Backtesting Engine

Backtest at the contract level with realistic execution: point-in-time data only; no look-ahead; correct historical contract availability; realistic bid/ask execution; slippage; broker/exchange fees; taxes and other costs; funding/financing where applicable; margin and leverage constraints; expiry and roll handling; position limits; latency assumptions for intraday strategies. Track Sharpe, Sortino, CAGR/return, maximum drawdown, win rate, profit factor, turnover, average holding time, capacity, tail losses, and performance by regime.

## 21. Risk Engine

Maximum position size; spread exposure; underlying exposure; margin utilization; stop/exit logic; maximum drawdown controls; liquidity limits; concentration across markets; correlation between simultaneous trades; stress testing.

## 22. Dashboard / Product Layer

Per market: live spot and futures curve; curve state (contango/backwardation); basis and basis %; slope and curvature; calendar-spread matrix; fair curve vs observed curve; deviation heatmap; z-score ranking; convergence probability; expected holding period; expected gross/net P&L; liquidity/cost estimate; trade-candidate ranking; historical behavior and backtest statistics.

## 23. Cross-Market Intelligence

After each individual market works reliably, compare relationships across markets: Gold–Silver; BTC–ETH; NIFTY–BANKNIFTY; crypto basis/funding vs broader crypto conditions; metals curves vs USD/rates/macro; index curves vs rates/volatility. A later research layer, not mixed into v1.

## 24. Recommended Build Order

Phase 1 Gold → data → normalized contracts → curve → basis → spreads → z-score → simple fair value → backtest. Phase 2 Silver. Phase 3 BTC (add perpetual/funding). Phase 4 ETH. Phase 5 NIFTY. Phase 6 BANKNIFTY. Phase 7 Cross-market. Phase 8 ML/prediction upgrades after reliable baselines.

## 25. Suggested Software Architecture

Data ingestion service; raw data store; normalized market-data database; contract/expiry master; curve construction module; feature-engineering module; statistical/fair-value engine; ML prediction service; regime engine; signal engine; backtesting engine; risk engine; monitoring/dashboard API; research notebooks.

## 26. Core Data Model

`timestamp | market | underlying | contract | expiry | days_to_expiry | spot | bid | ask | price | volume | open_interest | funding | basis | spread_id | fair_value | deviation | z_score | predicted_return | convergence_probability | expected_net_pnl | signal`

Keep raw observations separate from derived/model fields.

## 27. Example End-to-End Trade Candidate

Gold Feb = 7,500 and Gold Mar = 7,501. Observed spread = 1. Model fair spread = 8. Deviation = −7. Regime-adjusted z-score = −2.4. Model convergence probability = 78%. Expected convergence time = 3–5 days. Then check costs, liquidity, expiry, execution and risk. If expected net edge remains positive with acceptable risk, classify as a trade candidate — presented as evidence and a model output, not a guaranteed instruction to trade.

## 28. Critical Failure Modes

Look-ahead bias; survivorship bias; incorrect historical contract mapping; using only settlement/close prices and ignoring bid/ask; ignoring slippage and costs; ignoring liquidity; ignoring expiry effects; comparing maturities without controlling for time-to-expiry; overfitting ML models; data leakage during train/test splits; assuming statistical deviation always means mispricing; ignoring funding, financing, margin, or roll mechanics.

## 29. First Version — Minimum Viable Quant Engine

Do NOT start with a giant AI system. One market: Gold. Historical spot + futures data; contract normalization; curve reconstruction; basis calculation; all relevant pairwise spreads; rolling mean/std and z-scores; simple carry/fair-value model; convergence study; realistic cost model; walk-forward backtest; dashboard showing curve + anomalies. Once this works, generalize the same interfaces to Silver, BTC, ETH, NIFTY, and BANKNIFTY.

## 30. Final Mental Model

MARKET DATA → CONTRACTS → FUTURES CURVE → BASIS → CALENDAR SPREADS → CURVE SHAPE → FAIR VALUE → DEVIATION → Z-SCORE → PREDICTION → REGIME → COST/LIQUIDITY → RISK → SIGNAL → BACKTEST → LIVE MONITORING

The central research question is not "Are two futures prices close?" It is: "Given maturity, carry, market regime, liquidity and historical behavior, is the current relationship materially different from its estimated fair relationship, and is there enough expected net edge to justify the risk and execution costs?"

## 31. Learning Sequence Before Coding

Spot vs futures · expiry and convergence · basis · carry · contango and backwardation · calendar spreads · term structure / futures curve · curve slope and curvature · z-scores and mean reversion · fair-value modeling · PCA · time-series modeling · backtesting and bias control · ML for prediction · risk and execution.
