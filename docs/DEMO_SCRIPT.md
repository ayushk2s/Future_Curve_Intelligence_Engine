# Demo Video Script — Futures Curve Intelligence Engine

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
