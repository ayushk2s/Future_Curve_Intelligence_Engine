# Demo Video Script — Futures Curve Intelligence Engine

## OFFICIAL VERSION — matches the submission rubric (up to 5 min)

The hackathon requires the video to clearly cover five things, in order. This version is
labelled section-by-section so none of them get missed. Total run time ≈ 4:40–5:00.

**Setup (5 min):**
```bash
python3 demo.py --skip-fetch
python3 -m streamlit run app/dashboard.py
```
Open Gold tab → open BTC tab once (Backtest sub-tab) to warm it up → switch back to Gold.
Record **full screen** so you can Cmd+Tab to the terminal without stopping.

---

### 1 · THE PROBLEM (0:00–0:40)

**[Screen: title card or `docs/pipeline.png`]**

> "Every futures market — gold, Bitcoin, the Nifty — trades a *curve*: the same asset,
> priced differently at different future dates. That curve is a compressed statement of
> what the market charges to hold the asset through time — financing, storage, dividends,
> or for crypto, the funding rate.
>
> The problem is, most retail trading signals built off that curve are just noise. People
> see two contract prices that look 'close' or 'far apart' and call it a signal. It isn't.
> The real question is much harder: given the maturity, the true cost of carry, the current
> market regime, and the liquidity — is this curve *actually* mispriced, and does the edge
> survive real trading costs? Nobody was answering that question rigorously, so I built a
> system that does."

### 2 · HOW THE SOLUTION WORKS (0:40–1:35)

**[Screen: `docs/pipeline.png`, scroll slowly through the flow]**

> "It's one pipeline, applied to three markets — Gold on COMEX, and Bitcoin and Ethereum on
> Deribit. Five steps.
>
> One: it reconstructs the futures curve from raw contract data, cleaned to remove
> non-trading noise.
>
> Two: it fits a *fair value* for that curve from first principles — the actual cost of
> carrying the asset — not a guess, a regression fitted fresh every single day.
>
> Three: it measures how far the real market has drifted from that fair value, as a
> standardized score, and separately checks if that drift is explained by the market being
> in a stressed or trending regime.
>
> Four: it forecasts the next move and checks whether trading it would even survive fees and
> slippage.
>
> Five: only if all of that lines up does it produce a trade candidate — with a confidence
> score, not a guarantee."

### 3 · KEY FEATURES (1:35–2:15)

**[Screen: Dashboard, Gold tab, click through 2–3 tabs quickly]**

> "The dashboard shows this live for each market: the curve itself against its fair value,
> a heatmap of where every spread is statistically stretched, the current market regime, a
> ranked signal board of trade candidates with their expected cost-adjusted edge, and a full
> backtest with industry-standard metrics — Sharpe ratio, profit factor, max drawdown. There's
> also a monitor that watches for new deviations and writes out alerts automatically. Every
> number here is reproducible from raw data with a single command — nothing is hand-picked."

### 4 · THE ROLE OF AI (2:15–3:10)

**[Screen: Dashboard → any market → the tab showing the model forecast, if visible; otherwise stay on Signals tab]**

> "AI sits in two specific places, and I was deliberate about not overselling it.
>
> First, a walk-forward machine-learning model — gradient boosting — forecasts the next
> ten-day move in each spread. It's trained only on the past, retrained as new days arrive,
> and I measured its real skill out of sample: about a fifty-four percent hit rate. That's
> weak but genuinely real skill, not random. Because it's weak, I don't let it drive
> decisions alone — it only acts as a *confirming filter*: if the model disagrees with a
> trade, the system automatically sizes it down.
>
> Second, unsupervised clustering classifies the market into calm, normal, or stressed
> regimes, so the system knows when its own assumptions are less reliable.
>
> The honest role of AI here isn't to predict the future — it's to add a measured, tested
> opinion on top of a transparent statistical core, and to know its own limits. That's
> the difference between an intelligent system and a black box that happens to use AI."

### 5 · LIVE DEMONSTRATION (3:10–4:40)

**[Screen: Dashboard, Gold tab → Backtest tab]**

> "Here it is live. On Gold, the engine's verdict today is *stand aside* — its fair-value
> fit is ninety-nine-point-nine percent accurate, so there's nothing real to trade. And I
> can prove that's correct: a naive strategy that fades any statistical wobble gets a Sharpe
> ratio of minus two and draws down over four thousand dollars. My filtered version cuts
> that loss from eight percent to about one percent by trading sixty percent less."

**[Switch to BTC tab → Backtest sub-tab]**

> "Now Bitcoin — same engine, different market. It's watching the premium of dated futures
> over the perpetual swap versus what the funding rate implies. Blindly trading every rich
> basis: Sharpe minus zero-point-eight, a fifteen-thousand-dollar drawdown, roughly negative
> sixteen percent a year. Filtering for only the statistically extreme cases: twenty-nine
> trades, sixty-five percent win rate, Sharpe zero-point-eight-four, and about thirteen
> percent a year. Same market, same costs — the filter is the entire difference."

**[Cmd+Tab to terminal, run `python3 demo.py --skip-fetch`, let the table print]**

> "And this one command reproduces every number I just showed you, for all three markets,
> from raw data, in about ten seconds."

**[Back to dashboard or GitHub README, end card: link + disclaimer]**

> "It's in-sample, about a year of data — I'm not claiming a proven track record, I'm
> showing a rigorous, honest research process that knows when to say no trade. Code and the
> full write-up are linked below. Thanks for watching."

---

## LITE VERSION — one continuous take, ~2 min, 3 screens, no editing

Use this only if the 5-minute version above doesn't fit your remaining time.

Use this one if you're short on time. Full multi-scene version with shot list is below it.

**Setup (5 min):**
```bash
python3 demo.py --skip-fetch
python3 -m streamlit run app/dashboard.py
```
Open Gold tab → open BTC tab once (Backtest sub-tab) to warm it, then switch back to Gold —
that's your starting screen. Record **full screen** so you can Cmd+Tab to the terminal
without stopping the recording.

**[Screen: Dashboard, Gold tab, verdict + metrics row visible]**

> "Every futures market has a curve — same asset, different prices at different maturities.
> That curve tells you what it costs to hold the asset over time. I built an engine that
> checks if that curve is actually mispriced, and whether the edge survives real trading
> costs.
>
> Here it is on Gold, live. The engine's verdict is *stand aside* — the curve fits its
> fair-value model at ninety-nine-point-nine percent accuracy, so there's nothing real to
> trade. I can prove that's the right call, not laziness."

**[Click into Backtest tab — strategy table with Sharpe/drawdown visible]**

> "A naive strategy that fades every statistical wobble gets a Sharpe ratio of minus two —
> Sharpe ratio just means return per unit of risk taken, so a negative Sharpe means it loses
> money *and* it's volatile doing it. It also draws down over four thousand dollars on a
> fifty-thousand-dollar book. My filtered version — same market, same period — cuts the
> loss from eight percent to about one percent, with a much smaller drawdown, by simply
> trading sixty percent less. The discipline layer is the whole point."

**[Switch to BTC tab → Backtest sub-tab, let the harvest-vs-gated chart + table sit on screen]**

> "Now Bitcoin — same engine, different market. Here it's watching the premium of dated
> futures over the perpetual swap, versus what the funding rate implies they should be
> worth.
>
> If I blindly short every rich basis, no filtering: Sharpe minus zero-point-eight, a max
> drawdown of over fifteen thousand dollars — almost a third of the book — and a compound
> annual growth rate around negative sixteen percent. It loses.
>
> If I only trade when it's statistically extreme — this line — twenty-nine trades,
> sixty-five percent win rate, Sharpe zero-point-eight-four, max drawdown seven thousand,
> and a CAGR of about thirteen percent. Same market, same costs — the only difference is
> the filter. That's the actual edge: not the trade, the *selectivity*."

**[Cmd+Tab to terminal, run `python3 demo.py --skip-fetch`, let the table print]**

> "One command reproduces every number I just said — Gold, Bitcoin, Ethereum, all four
> backtests. It's in-sample, about a year of data, twenty to thirty trades per strategy —
> I'm not calling this a proven track record, I'm showing an honest research process that
> knows when to say no trade. Code and the full write-up are linked below. Thanks for
> watching."

**Timing:** ~2:00–2:10. Do 2–3 takes, keep the smoothest. Trim only the dead air at the
very start/end — no scene cuts needed.

---


Target length: **2:15–2:30** (fits any 2–3 min Devpost cap). A 60-second trim is marked
at the bottom for a stricter cap — check the AI Builders submission page for the exact limit.

Read every line in first person — this is a solo build.

---

## Before you hit record — 10-minute checklist

```bash
cd ~/Documents/future_curve_model
python3 demo.py --skip-fetch          # confirms everything still runs, warms the data
python3 -m streamlit run app/dashboard.py
```

- [ ] Close Slack/notifications, silence phone, full-screen the browser (hide bookmarks bar)
- [ ] Zoom the browser to ~110–125% so text is readable on a recorded video
- [ ] Pre-navigate the dashboard once so tab-switches are instant when recording (no lag)
- [ ] Have a second terminal tab ready with `python3 demo.py --skip-fetch` **not yet run**
      (you'll run it live so the printed table appears on screen)
- [ ] Record in one take if you can; otherwise record scene-by-scene (markers below) and
      cut together — easier than one perfect take
- [ ] macOS screen recording: `Cmd+Shift+5` → record selected portion at 1920×1080 if possible
- [ ] Record narration separately if your mic is bad, then sync in edit — cleaner audio wins
      more than perfect screen timing

---

## SCENE 1 — Hook (0:00–0:15)

**Screen:** Start on a blank terminal or a title card (repo README rendered on GitHub, or
`docs/pipeline.png` full-screen).

**Say:**
> "Every futures market has a curve — the price of the same asset at different maturities.
> That curve tells you what the market charges to hold an asset through time. Most trading
> signals built off it are noise — two contracts being close is not an opportunity. I built
> an engine that answers the actual question: is today's curve *really* mispriced, and does
> the edge survive real costs — across Gold, Bitcoin, and Ethereum."

---

## SCENE 2 — What it does, fast (0:15–0:35)

**Screen:** `docs/pipeline.png` (or scroll the README to the diagram).

**Say:**
> "One pipeline. It reconstructs the futures curve, fits a fair value from the actual cost
> of carrying the asset, measures how far reality strays from that fair value, checks the
> market regime, forecasts the next move, filters out anything that can't survive
> transaction costs, and only then calls something a trade candidate. Then it backtests the
> whole thing, walk-forward, with no look-ahead."

---

## SCENE 3 — Live dashboard: Gold says "no" (0:35–1:00)

**Screen:** Dashboard → Gold tab, top metrics row visible.

**Say:**
> "Here's Gold, live. The engine fits gold's curve to the cost-of-carry model at
> ninety-nine-point-nine percent accuracy. And its verdict today is: stand aside. Why?
> Because I proved it — [switch to Backtest tab] — a naive strategy that just fades any
> statistical wobble loses eight percent. My fully-gated version, with cost and regime
> filters, cuts that loss to just over one percent by trading sixty percent less. The engine
> doesn't invent a trade when there isn't one."

**Action:** click through Curve & Fair Value tab briefly, then Backtest tab, point at the
equity curves (A vs C).

---

## SCENE 4 — Live dashboard: BTC finds something real (1:00–1:35)

**Screen:** Switch sidebar to BTC.

**Say:**
> "Now Bitcoin. Same engine, different market — here the tradeable thing is the premium of
> a dated future over the perpetual swap, versus what the funding rate says it should be.
> [point at Basis vs Funding tab] Right now a few quarterly contracts are trading rich. [go
> to Backtest tab] And this is the proof that matters: if I blindly short every rich basis,
> I lose seventeen percent. If I only trade when it's statistically extreme — this orange
> line — I make fourteen percent, Sharpe zero-point-eight-four. The filter is the edge, not
> just riding the trend."

**Action:** show the harvest-vs-gated chart clearly, let it sit on screen for 2–3 seconds.

---

## SCENE 5 — One-command proof + credibility (1:35–1:55)

**Screen:** Switch to terminal, run:
```bash
python3 demo.py --skip-fetch
```
Let the results table print on screen.

**Say:**
> "Everything here is reproducible in one command — it fetches the data, runs the full
> pipeline for all three markets, and prints this exact scoreboard. I also wrote tests that
> directly check there's no look-ahead bias in the statistics — the single most common way a
> backtest lies to you."

**Action:** briefly flash `tests/test_pipeline.py` or the `10 passed` pytest output if you
have it ready in a second terminal.

---

## SCENE 6 — Honest close (1:55–2:20)

**Screen:** Back to dashboard or the README on GitHub.

**Say:**
> "This is in-sample, about a year of data, a few dozen trades — I'm not claiming a proven
> track record, I'm showing a rigorous research process that's honest about what it doesn't
> know. That honesty — refusing to invent an edge on Gold, and proving *why* the filter works
> on Bitcoin — is the actual result. Code, the full explainer, and the dashboard are linked
> below. Thanks for watching."

**Screen (end card, 2–3 sec):** GitHub link + "Not investment advice" line, large and readable.

---

## 60-SECOND CUT (if the hackathon caps it tighter)

1. **(0:00–0:12)** Scene 1's hook, trimmed to the first two sentences.
2. **(0:12–0:32)** Scene 3, gold verdict + the A vs C backtest chart only.
3. **(0:32–0:52)** Scene 4, BTC harvest-vs-gated chart only — this is the single most
   compelling visual, don't cut it even under time pressure.
4. **(0:52–1:00)** One line: *"One engine, three markets, honest about where the edge is.
   Link below — not investment advice."*

---

## Delivery tips

- Speak ~10% slower than feels natural — screen recordings always feel rushed on playback.
- Say numbers plainly: "eight percent", not "8%" mentally — it reads better on camera.
- If you stumble, pause 2 seconds and redo the sentence — trim the gap in editing rather
  than restarting the whole scene.
- Cursor movement: move deliberately and pause on what you want the viewer to read; don't
  wave the mouse while talking.
- Free editing: iMovie (already on macOS) is enough — cut scenes at the markers above, add
  the end card, export 1080p.
