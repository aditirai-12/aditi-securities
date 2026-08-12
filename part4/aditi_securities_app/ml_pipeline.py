# Aditi Rai
# Aditi Securities - Project Part IV
# Data-driven program module. This is the piece the assignment calls out
# specifically: it "manages the data pipeline for unstructured data and
# enables seamless re-training of the machine-learning model upon changes to
# the corresponding source of unstructured data." It is a refactor of Part
# III's train_ml_model.py into importable functions, plus:
#   - data_fingerprint()/should_retrain(): cheap change detection over the
#     raw price CSVs, so the app only pays the retraining cost when the
#     underlying data actually changed, with no human having to trigger it.
#   - refresh_portfolio_risk_summary(): writes the model's output back into
#     the OLTP database (PORTFOLIO_RISK_SUMMARY), which is the "update the
#     OLTP/ODS database to consider insights obtained by applying a machine
#     learning model" requirement from the Part IV spec.

import glob
import hashlib
import json
import os
from datetime import datetime, date

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from models import Holding, SecuritySignal, PortfolioRiskSummary

FEATURES = ["Lag1_return", "Lag2_return", "MA5", "Price_vs_MA5", "Price_vs_MA10",
            "Volatility5", "Volume_change"]


def _prices_dir(data_dir):
    return os.path.join(data_dir, "raw", "prices")


def load_all_prices(data_dir):
    frames = []
    for path in sorted(glob.glob(f"{_prices_dir(data_dir)}/*.csv")):
        ticker = os.path.basename(path).split("_")[0]
        df = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
        df["Ticker"] = ticker
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def engineer_features(df):
    out = []
    for ticker, g in df.groupby("Ticker"):
        g = g.sort_values("Date").reset_index(drop=True)
        g["Daily_return"] = g["Close"].pct_change()
        g["Lag1_return"] = g["Daily_return"].shift(1)
        g["Lag2_return"] = g["Daily_return"].shift(2)
        g["MA5"] = g["Close"].rolling(5).mean()
        g["MA10"] = g["Close"].rolling(10).mean()
        g["Price_vs_MA5"] = (g["Close"] - g["MA5"]) / g["MA5"]
        g["Price_vs_MA10"] = (g["Close"] - g["MA10"]) / g["MA10"]
        g["Volatility5"] = g["Daily_return"].rolling(5).std()
        g["Volume_change"] = g["Volume"].pct_change()
        g["Next_return"] = g["Daily_return"].shift(-1)
        g["Target_up"] = (g["Next_return"] > 0).astype(int)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def data_fingerprint(data_dir):
    """Cheap fingerprint of the raw price CSVs (row count + last-modified
    time per file). Changes whenever new price rows are collected, without
    needing to hash the full file contents on every request."""
    parts = []
    for path in sorted(glob.glob(f"{_prices_dir(data_dir)}/*.csv")):
        stat = os.stat(path)
        with open(path) as f:
            nrows = sum(1 for _ in f)
        parts.append(f"{os.path.basename(path)}:{nrows}:{int(stat.st_mtime)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def should_retrain(state_path, data_dir):
    current = data_fingerprint(data_dir)
    if not os.path.exists(state_path):
        return True, current
    with open(state_path) as f:
        state = json.load(f)
    return state.get("fingerprint") != current, current


def train_model(data_dir):
    raw = load_all_prices(data_dir)
    feat = engineer_features(raw)
    model_df = feat.dropna(subset=FEATURES + ["Target_up"]).reset_index(drop=True)

    X = model_df[FEATURES].values
    y = model_df["Target_up"].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    scaler = StandardScaler().fit(X_train)
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(scaler.transform(X_train), y_train)
    test_acc = model.score(scaler.transform(X_test), y_test)

    version = "logreg-" + datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    bundle = {
        "model": model, "scaler": scaler, "features": FEATURES,
        "version": version, "test_accuracy": float(test_acc),
        "n_rows": int(len(model_df)), "trained_at": datetime.utcnow().isoformat(),
    }
    return bundle, feat


def save_model(bundle, path):
    joblib.dump(bundle, path)


def load_model(path):
    return joblib.load(path)


def predict_for_ticker(bundle, feat_df, ticker):
    """Latest available feature row for a ticker -> predicted probability
    that the next trading day's return is positive."""
    rows = feat_df[(feat_df["Ticker"] == ticker)].dropna(subset=bundle["features"])
    if rows.empty:
        return None
    latest = rows.sort_values("Date").iloc[-1]
    X = latest[bundle["features"]].values.reshape(1, -1)
    prob_up = bundle["model"].predict_proba(bundle["scaler"].transform(X))[0][1]
    return float(prob_up), latest["Date"].date()


def refresh_portfolio_risk_summary(session, bundle, feat_df, data_dir):
    """Recompute PORTFOLIO_RISK_SUMMARY for every HOLDING, combining the
    Part III signal aggregates with the live model score -- the ORM
    equivalent of the INSERT ... ON DUPLICATE KEY UPDATE refresh statement
    in part3_physical_design.sql, extended with the ML output."""
    holdings = session.query(Holding).all()
    now = datetime.utcnow()
    for h in holdings:
        ticker = h.security.Ticker
        pred = predict_for_ticker(bundle, feat_df, ticker)
        prob_up, signal_date = pred if pred else (None, None)

        signals = session.query(SecuritySignal).filter(SecuritySignal.Security_id == h.Security_id).all()
        news_sentiment = next((s.Signal_value for s in signals if s.Signal_type == "News_sentiment"), None)
        price_return = next((s.Signal_value for s in signals if s.Signal_type == "Price_3mo_return"), None)
        risk_mentions = sum(1 for s in signals if s.Signal_type.startswith("Risk_mention"))
        latest_signal_date = max((s.Signal_date for s in signals), default=signal_date)

        row = session.get(PortfolioRiskSummary, (h.Portfolio_id, h.Security_id))
        if row is None:
            row = PortfolioRiskSummary(Portfolio_id=h.Portfolio_id, Security_id=h.Security_id)
            session.add(row)
        row.Quantity = h.Quantity
        row.Latest_signal_date = latest_signal_date
        row.News_sentiment = news_sentiment
        row.Price_3mo_return = price_return
        row.Open_risk_mentions = risk_mentions
        row.Predicted_up_probability = prob_up
        row.Model_version = bundle["version"]
        row.Last_refreshed = now
    session.commit()


def retrain_if_needed(session, data_dir, model_path, state_path, force=False):
    """Entry point called by the Flask app on every quote request (cheap
    fingerprint check) and by the admin retrain endpoint (force=True).
    Returns (retrained: bool, bundle, feat_df)."""
    need_retrain, fingerprint = should_retrain(state_path, data_dir)
    if not (need_retrain or force) and os.path.exists(model_path):
        bundle = load_model(model_path)
        raw = load_all_prices(data_dir)
        feat_df = engineer_features(raw)
        return False, bundle, feat_df

    bundle, feat_df = train_model(data_dir)
    save_model(bundle, model_path)
    with open(state_path, "w") as f:
        json.dump({"fingerprint": fingerprint, "trained_at": bundle["trained_at"],
                    "version": bundle["version"]}, f)
    refresh_portfolio_risk_summary(session, bundle, feat_df, data_dir)
    return True, bundle, feat_df
