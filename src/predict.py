"""
Step 11 — PREDICTION ENGINE  (blueprint sections 14, 16)

Target: the change in each adjacent calendar spread over the next H=10 trading
days.   y = spread(t+H) - spread(t)

Three models, walk-forward (expanding window, retrain every RETRAIN days), all
strictly point-in-time:

  OU      analytic mean-reversion:  y_hat = -(1 - rho^H) * (spread_t - mu_pit)
  RIDGE   linear, L2-regularised, on standardised features
  GBR     GradientBoostingRegressor (shallow) -- the "ML" model
  ENS     average of RIDGE and GBR

The 4 spreads are POOLED into one training set (they share one driver -> more
data, less overfit). Reports OUT-OF-SAMPLE skill: correlation and hit-rate of
predicted vs realised change, per model.

Output: data/clean/predictions.csv   (per date x spread: y_hat per model + realised y)

Run:  python src/predict.py
"""

import pathlib
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

from _paths import CLEAN_DIR as CLEAN
SPREADS = ["cs_Z_V", "cs_G_Z", "cs_J_G", "cs_M_J"]
NEAR_LEG = {"cs_Z_V": "V26", "cs_G_Z": "Z26", "cs_J_G": "G27", "cs_M_J": "J27"}
H = 10
RETRAIN = 20
START_MIN = 90          # need this many rows before first prediction

# note: slope_ann is intentionally excluded -- it is ~ the sum of the adjacent
# spreads (see curve-shape lesson Q3), so it adds collinearity, not information.
FEATURES = ["spread", "gap_pit", "z_hist", "z_fair", "mom_5d",
            "curvature", "implied_carry", "z_carry",
            "realised_vol", "ret_20d", "near_dte"]


def assemble() -> pd.DataFrame:
    feats = pd.read_csv(CLEAN / "features.csv", parse_dates=["date"]).set_index("date")
    dev = pd.read_csv(CLEAN / "deviation.csv", parse_dates=["date"]).set_index("date")
    fv = pd.read_csv(CLEAN / "fairvalue.csv", parse_dates=["date"]).set_index("date")
    reg = pd.read_csv(CLEAN / "regime.csv", parse_dates=["date"]).set_index("date")
    long = pd.read_csv(CLEAN / "curve_long.csv", parse_dates=["date"])
    dte = long.pivot(index="date", columns="contract", values="days_to_expiry")
    dte.columns = [c[2:5] for c in dte.columns]

    frames = []
    for sp in SPREADS:
        mu_pit = feats[sp].rolling(60, min_periods=20).mean().shift(1)
        df = pd.DataFrame(index=feats.index)
        df["spread_name"] = sp
        df["spread"] = feats[sp]
        df["gap_pit"] = feats[sp] - mu_pit
        df["z_hist"] = dev[f"z_hist_{sp}"]
        df["z_fair"] = dev[f"z_fair_devspread_{sp}"]
        df["mom_5d"] = feats[sp] - feats[sp].shift(5)
        df["curvature"] = feats["curvature"]
        df["slope_ann"] = feats["slope_ann"]
        df["implied_carry"] = fv["implied_carry"]
        df["z_carry"] = dev["z_carry"]
        df["realised_vol"] = reg["realised_vol"]
        df["ret_20d"] = reg["ret_20d"]
        df["near_dte"] = dte[NEAR_LEG[sp]]
        df["y"] = feats[sp].shift(-H) - feats[sp]          # realised forward change
        # OU pieces
        x = (feats[sp] - feats[sp].mean())
        rho = float(np.dot(x.values[:-1], x.values[1:]) / np.dot(x.values[:-1], x.values[:-1]))
        df["ou_pred"] = -(1 - rho ** H) * df["gap_pit"]
        frames.append(df.reset_index())

    out = pd.concat(frames, ignore_index=True).sort_values(["date", "spread_name"])
    return out.replace([np.inf, -np.inf], np.nan)


def walk_forward(data: pd.DataFrame) -> pd.DataFrame:
    dates = np.array(sorted(data["date"].unique()))
    preds = []
    model_ridge = model_gbr = None
    scaler = None

    for i, d in enumerate(dates):
        train = data[(data["date"] < d) & data["y"].notna()].dropna(subset=FEATURES + ["y"])
        cur = data[data["date"] == d].dropna(subset=FEATURES)
        if len(train) < START_MIN or cur.empty:
            continue
        if (model_ridge is None) or (i % RETRAIN == 0):
            scaler = StandardScaler().fit(train[FEATURES].values)
            scaler.scale_[scaler.scale_ == 0] = 1.0        # guard constant columns
            Xtr = np.nan_to_num(scaler.transform(train[FEATURES].values))
            ytr = train["y"].values
            model_ridge = Ridge(alpha=10.0, solver="cholesky").fit(Xtr, ytr)
            model_gbr = GradientBoostingRegressor(
                n_estimators=120, max_depth=2, learning_rate=0.03,
                subsample=0.8, random_state=0).fit(Xtr, ytr)

        Xc = np.nan_to_num(scaler.transform(cur[FEATURES].values))
        pr, pg = model_ridge.predict(Xc), model_gbr.predict(Xc)
        for k, (_, row) in enumerate(cur.iterrows()):
            preds.append({
                "date": d, "spread_name": row["spread_name"],
                "y_real": row["y"], "ou_pred": row["ou_pred"],
                "ridge_pred": pr[k], "gbr_pred": pg[k],
                "ens_pred": 0.5 * (pr[k] + pg[k]),
            })
    return pd.DataFrame(preds)


def report(p: pd.DataFrame) -> None:
    ok = p.dropna(subset=["y_real"])
    print(f"out-of-sample predictions: {len(ok)} rows "
          f"({ok['date'].min().date()} .. {ok['date'].max().date()})\n")
    print(f"{'model':6s} {'corr':>8s} {'hit_rate':>9s} {'MAE':>8s}")
    for col in ["ou_pred", "ridge_pred", "gbr_pred", "ens_pred"]:
        s = ok.dropna(subset=[col])
        corr = np.corrcoef(s[col], s["y_real"])[0, 1]
        hit = (np.sign(s[col]) == np.sign(s["y_real"])).mean()
        mae = (s[col] - s["y_real"]).abs().mean()
        print(f"{col.split('_')[0]:6s} {corr:8.3f} {hit:9.3f} {mae:8.3f}")
    print("\nhit_rate > 0.5 and positive corr = the model has *some* directional skill.")
    print("with ~240 days this is noisy; treat as a weak prior, not a crystal ball.")


def build() -> None:
    data = assemble()
    preds = walk_forward(data)
    preds.to_csv(CLEAN / "predictions.csv", index=False)
    print(f"wrote {CLEAN / 'predictions.csv'}\n")
    report(preds)


if __name__ == "__main__":
    build()
