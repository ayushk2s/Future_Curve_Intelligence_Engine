"""
DASHBOARD / PRODUCT LAYER  (blueprint section 22)

    streamlit run dashboard.py

Pick the market in the sidebar. Run the pipelines first:
    python pipeline.py            # gold
    python crypto_pipeline.py     # BTC + ETH
"""

import pathlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

ROOT = pathlib.Path(__file__).resolve().parents[1]   # repo root
st.set_page_config(page_title="Futures Curve Intelligence", layout="wide")


@st.cache_data
def rd(path, parse_date=True):
    p = pathlib.Path(path)
    if not p.exists():
        return None
    return pd.read_csv(p, **({"parse_dates": ["date"]} if parse_date else {}))


# ============================================================ GOLD
def render_gold():
    C, O = ROOT / "data/clean", ROOT / "data/output"
    SPREADS = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]
    ORDER = ["GCV26.CMX", "GCZ26.CMX", "GCG27.CMX", "GCJ27.CMX", "GCM27.CMX"]

    feats = rd(C / "features.csv"); fv = rd(C / "fairvalue.csv"); dev = rd(C / "deviation.csv")
    reg = rd(C / "regime.csv"); sig = rd(C / "signals.csv"); long = rd(C / "curve_long.csv")
    conv = rd(C / "convergence.csv", False); eq = rd(O / "bt_equity.csv"); mets = rd(O / "bt_metrics.csv", False)
    if feats is None:
        st.error("Run:  python pipeline.py"); return
    for d in (feats, fv, dev, reg):
        d.set_index("date", inplace=True)
    last = feats.index.max()

    st.title("🟡 Gold (COMEX) — Futures Curve Intelligence")
    st.caption(f"as of **{last.date()}**")
    c = st.columns(5)
    c[0].metric("Curve state", "Contango" if feats["cs_Z_V"].iloc[-1] > 0 else "Backwardation")
    c[1].metric("Implied carry", f"{fv['implied_carry'].iloc[-1]*100:.2f}%/yr")
    c[2].metric("Carry-fit R²", f"{fv['fit_r2'].iloc[-1]:.4f}")
    c[3].metric("Regime", f"{reg['regime_vol'].iloc[-1]}/{reg['regime_trend'].iloc[-1]}")
    cand = sig[(sig.date == last) & sig.trade_candidate] if sig is not None else pd.DataFrame()
    c[4].metric("Verdict", "TRADE CANDIDATE" if len(cand) else "STAND ASIDE")

    t = st.tabs(["Curve & Fair Value", "Spreads & Deviation", "Regime", "Signals", "Backtest", "Convergence"])

    with t[0]:
        snap = long[long.date == last].sort_values("T")
        fvrow = fv.loc[last]
        fair = [fvrow[f"fair_{s[2:5]}"] for s in ORDER]
        fig = go.Figure()
        fig.add_scatter(x=snap["T"], y=snap["close"], mode="lines+markers", name="observed", line=dict(width=3))
        fig.add_scatter(x=snap["T"], y=fair, mode="lines+markers", name="carry fair value", line=dict(dash="dash"))
        fig.update_layout(title="Futures curve vs cost-of-carry fair value",
                          xaxis_title="years to expiry", yaxis_title="$/oz", height=430)
        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(px.line(fv.reset_index(), x="date", y="implied_carry", height=300,
                                title="Implied carry rate (r+s−y) over time"), use_container_width=True)

    with t[1]:
        rows = [{"spread": s, "observed": round(feats[s].iloc[-1], 2),
                 "fair": round(fv[f"fair_{s}"].iloc[-1], 2),
                 "gap": round(feats[s].iloc[-1] - fv[f"fair_{s}"].iloc[-1], 2),
                 "z_hist": round(dev[f"z_hist_{s}"].iloc[-1], 2),
                 "z_fair": round(dev[f"z_fair_devspread_{s}"].iloc[-1], 2)} for s in SPREADS]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        zf = pd.DataFrame({s: dev[f"z_fair_devspread_{s}"] for s in SPREADS}).dropna().tail(160)
        st.plotly_chart(px.imshow(zf.T, aspect="auto", color_continuous_scale="RdBu_r", zmin=-3, zmax=3,
                                  origin="lower", title="Deviation heatmap — z_fair (σ)", height=280),
                        use_container_width=True)
        pick = st.selectbox("Inspect", SPREADS, index=1)
        s = feats[pick]; mu = s.rolling(60, min_periods=20).mean().shift(1); sd = s.rolling(60, min_periods=20).std().shift(1)
        fig = go.Figure()
        fig.add_scatter(x=s.index, y=s, name="observed")
        fig.add_scatter(x=s.index, y=fv[f"fair_{pick}"], name="carry fair", line=dict(dash="dash"))
        fig.add_scatter(x=s.index, y=mu + 2*sd, name="+2σ", line=dict(width=0.5, color="grey"))
        fig.add_scatter(x=s.index, y=mu - 2*sd, name="−2σ", line=dict(width=0.5, color="grey"),
                        fill="tonexty", fillcolor="rgba(128,128,128,0.12)")
        fig.update_layout(height=380, title=f"{pick}: observed vs fair vs ±2σ")
        st.plotly_chart(fig, use_container_width=True)

    with t[2]:
        r = reg.reset_index()
        st.plotly_chart(px.scatter(r, x="date", y="realised_vol", color="regime_vol", height=340,
                        color_discrete_map={"calm": "#2ca02c", "normal": "#1f77b4", "stressed": "#d62728"}),
                        use_container_width=True)
        st.info("Signals are down-weighted in stressed / strongly-trending regimes (§17).")

    with t[3]:
        if sig is None:
            st.warning("run signals.py")
        else:
            show = sig[sig.date == last][["spread", "actual", "fair", "fair_gap", "z_fair", "gbr_pred",
                                          "direction", "model_agree", "regime_vol", "adj_net_pts",
                                          "signal_score", "trade_candidate"]]
            st.dataframe(show, hide_index=True, use_container_width=True)
            if len(cand):
                for _, r in cand.iterrows():
                    st.success(f"{'LONG' if r.direction>0 else 'SHORT'} {r.spread} · score {r.signal_score}")
            else:
                st.warning("No trade candidate today — expected edge does not clear costs / regime filter.")

    with t[4]:
        if eq is None:
            st.warning("run backtest.py")
        else:
            e = eq.copy(); e["date"] = pd.to_datetime(e["date"])
            fig = go.Figure()
            for col, nm in {"equity_A": "A naive z_hist fade", "equity_B": "B fair-value fade",
                            "equity_C": "C gated (discipline)", "equity_D": "D model momentum"}.items():
                if col in e:
                    fig.add_scatter(x=e.date, y=e[col], name=nm)
            fig.update_layout(height=380, yaxis_title="realised P&L ($)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(mets, hide_index=True, use_container_width=True)
            st.info("Naive fading (A) bleeds ~7× the gated engine (C). No positive edge on gold "
                    "after costs — the engine correctly says *stand aside*.")

    with t[5]:
        if conv is None:
            st.warning("run convergence.py")
        else:
            pooled = (conv[conv.horizon == 10].groupby(["z_lo", "z_hi"]).apply(
                lambda g: pd.Series({"n": int(g["n"].sum()),
                                     "p_revert": round(np.average(g.p_revert, weights=g.n), 3),
                                     "gap_captured": round(np.average(g.mean_gap_captured, weights=g.n), 3)}),
                include_groups=False).reset_index())
            st.dataframe(pooled, hide_index=True, use_container_width=True)
            st.caption("p_revert < 0.5 across buckets ⇒ gold spreads trended, not reverted, in this sample. "
                       "That is *why* the naive mean-reversion backtest loses.")


# ============================================================ CRYPTO
def render_crypto(ccy: str):
    C = ROOT / f"data/crypto/{ccy}/clean"
    O = ROOT / f"data/crypto/{ccy}/output"
    f = rd(C / "features.csv"); sig = rd(C / "signals.csv"); long = rd(C / "curve_long.csv")
    eq = rd(O / "bt_equity.csv"); mets = rd(O / "bt_metrics.csv", False)
    if f is None:
        st.error(f"Run:  python crypto_pipeline.py   (missing {ccy})"); return
    f.set_index("date", inplace=True)
    last = f.index.max()
    tags = [c.split("_", 1)[1] for c in f.columns if c.startswith("qbasis_")]

    st.title(f"{'🟠' if ccy=='BTC' else '🟣'} {ccy} — Futures Curve Intelligence (perp + dated)")
    st.caption(f"as of **{last.date()}** · tradeable object: dated-future premium over perp vs funding-implied fair value")
    c = st.columns(5)
    c[0].metric("Index", f"{f['index'].iloc[-1]:,.0f}")
    c[1].metric("Perp basis", f"{f['perp_basis_bp'].iloc[-1]:+.1f} bp")
    c[2].metric("Funding (7d ann)", f"{f['funding_ann_7d'].iloc[-1]*100:+.2f}%")
    c[3].metric("Curve carry", f"{f['implied_carry'].iloc[-1]*100:+.2f}%",
                f"{f['carry_vs_funding'].iloc[-1]*100:+.2f}% vs funding")
    cand = sig[(sig.date == last) & sig.trade_candidate] if sig is not None else pd.DataFrame()
    c[4].metric("Verdict", f"{len(cand)} CANDIDATE(S)" if len(cand) else "STAND ASIDE")

    t = st.tabs(["Curve & Funding", "Basis vs Funding", "Signals", "Backtest"])

    with t[0]:
        snap = long[long.date == last].sort_values("T")
        fig = go.Figure()
        fig.add_scatter(x=snap["T"], y=snap["close"], mode="lines+markers", name="observed", line=dict(width=3))
        # funding-implied fair curve
        idx0 = f["index"].iloc[-1]; fnd = f["funding_ann_7d"].iloc[-1]
        fig.add_scatter(x=snap["T"], y=idx0 * (1 + fnd * snap["T"]), mode="lines", name="funding-implied",
                        line=dict(dash="dash"))
        fig.update_layout(title=f"{ccy} curve vs funding-implied fair value", xaxis_title="years to expiry",
                          yaxis_title="price", height=420)
        st.plotly_chart(fig, use_container_width=True)
        fig2 = go.Figure()
        fig2.add_scatter(x=f.index, y=f["funding_ann_7d"] * 100, name="funding 7d ann %")
        fig2.add_scatter(x=f.index, y=f["implied_carry"] * 100, name="curve-implied carry %")
        fig2.update_layout(height=320, title="Curve-implied carry vs funding (the dislocation)")
        st.plotly_chart(fig2, use_container_width=True)

    with t[1]:
        rows = [{"contract": tg, "qbasis $": round(f[f"qbasis_{tg}"].iloc[-1], 1),
                 "funding-fair $": round(f[f"fair_qbasis_{tg}"].iloc[-1], 1),
                 "gap $": round(f[f"gap_{tg}"].iloc[-1], 1),
                 "z_gap": round(f[f"z_gap_{tg}"].iloc[-1], 2),
                 "carry_gap ann %": round(f[f"carry_gap_ann_{tg}"].iloc[-1] * 100, 2)} for tg in tags]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        zf = pd.DataFrame({tg: f[f"z_gap_{tg}"] for tg in tags}).dropna().tail(200)
        st.plotly_chart(px.imshow(zf.T, aspect="auto", color_continuous_scale="RdBu_r", zmin=-3, zmax=3,
                                  origin="lower", title="z_gap heatmap (dated future vs funding-fair, σ)", height=260),
                        use_container_width=True)
        pick = st.selectbox("Inspect", tags, index=min(1, len(tags) - 1))
        fig = go.Figure()
        fig.add_scatter(x=f.index, y=f[f"qbasis_{pick}"], name="qbasis (dated − perp)")
        fig.add_scatter(x=f.index, y=f[f"fair_qbasis_{pick}"], name="funding-implied fair", line=dict(dash="dash"))
        fig.update_layout(height=360, title=f"{ccy} {pick}: premium over perp vs funding-fair")
        st.plotly_chart(fig, use_container_width=True)

    with t[2]:
        if sig is None:
            st.warning("run crypto engine")
        else:
            st.dataframe(sig[sig.date == last][["spread", "actual", "fair", "fair_gap", "z_fair",
                         "carry_gap_ann", "direction", "regime_vol", "regime_funding",
                         "adj_net_pts", "signal_score", "trade_candidate"]],
                         hide_index=True, use_container_width=True)
            for _, r in cand.iterrows():
                st.success(f"{'LONG' if r.direction>0 else 'SHORT'} {r.spread} · z {r.z_fair} · "
                           f"score {r.signal_score} · exp net ${r.adj_net_pts}/lot")
            if not len(cand):
                st.warning("No candidate today — basis is close to funding-fair, or edge < fees.")

    with t[3]:
        if eq is None:
            st.warning("run crypto engine")
        else:
            e = eq.copy(); e["date"] = pd.to_datetime(e["date"])
            fig = go.Figure()
            for col, nm in {"equity_harvest": "harvest — short every contango basis",
                            "equity_gated": "gated — only when z_gap ≥ 1.25"}.items():
                if col in e:
                    fig.add_scatter(x=e.date, y=e[col], name=nm)
            fig.update_layout(height=360, yaxis_title="realised P&L ($, $50k book)",
                              title=f"{ccy} — does the z-score filter beat blind basis harvesting?")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(mets, hide_index=True, use_container_width=True)
            st.info("Blindly harvesting every contango basis LOSES (fees + funding + getting run "
                    "over when basis widens). The z-score filter — enter only when a dated future "
                    "is statistically rich vs funding — is what turns it positive. "
                    "Still: one year of data, one funding regime, ~30 trades. Paper-trade first.")


# ============================================================ shell
st.sidebar.header("Market")
market = st.sidebar.radio("Select", ["Gold (COMEX)", "BTC (Deribit)", "ETH (Deribit)"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("pipelines:\n\n`python pipeline.py`\n\n`python crypto_pipeline.py`")

if market.startswith("Gold"):
    render_gold()
elif market.startswith("BTC"):
    render_crypto("BTC")
else:
    render_crypto("ETH")

st.divider()
st.caption("Research / decision-support only. Not investment advice. Validate out-of-sample and "
           "paper-trade before risking capital.")
