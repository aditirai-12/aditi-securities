# Aditi Rai
# Aditi Securities - Project Part III: machine learning model
#
# Business use case: forecast whether a security's price will move up or
# down the next trading day, using technical features derived from the
# Part II data lake's raw price history (datalake/raw/prices/*.csv). This
# supports the risk-forecasting use case from Part II (Section 1 -
# forecasting security/portfolio risk from market factors) by giving
# compliance/advisory a leading indicator per holding, which feeds the
# PORTFOLIO_RISK_SUMMARY table added in the Part III physical design.

import glob
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

DATA_DIR = "/sessions/confident-inspiring-fermi/mnt/outputs/datalake/raw/prices"
OUT_DIR = "/sessions/confident-inspiring-fermi/mnt/outputs"

def load_all_prices():
    frames = []
    for path in sorted(glob.glob(f"{DATA_DIR}/*.csv")):
        ticker = path.split("/")[-1].split("_")[0]
        df = pd.read_csv(path, parse_dates=["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
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
        # target: did the price go up the NEXT trading day?
        g["Next_return"] = g["Daily_return"].shift(-1)
        g["Target_up"] = (g["Next_return"] > 0).astype(int)
        out.append(g)
    full = pd.concat(out, ignore_index=True)
    return full

FEATURES = ["Lag1_return", "Lag2_return", "MA5", "Price_vs_MA5", "Price_vs_MA10",
            "Volatility5", "Volume_change"]

def main():
    log = []
    def p(msg=""):
        print(msg)
        log.append(str(msg))

    raw = load_all_prices()
    p(f"Loaded {len(raw)} daily price rows across {raw['Ticker'].nunique()} tickers "
      f"({', '.join(sorted(raw['Ticker'].unique()))}).")

    feat = engineer_features(raw)
    model_df = feat.dropna(subset=FEATURES + ["Target_up"]).reset_index(drop=True)
    p(f"After feature engineering (5/10-day rolling windows) and dropping "
      f"warm-up rows: {len(model_df)} usable rows.")
    p(f"Class balance (Target_up): {model_df['Target_up'].value_counts().to_dict()}")

    X = model_df[FEATURES].values
    y = model_df["Target_up"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    p("\n=== Logistic Regression ===")
    logreg = LogisticRegression(max_iter=1000, random_state=42)
    logreg.fit(X_train_s, y_train)
    pred_lr = logreg.predict(X_test_s)
    acc_lr = accuracy_score(y_test, pred_lr)
    p(f"Test accuracy: {acc_lr:.3f}")
    p(f"Confusion matrix [[TN FP][FN TP]]:\n{confusion_matrix(y_test, pred_lr)}")
    p("Coefficients (standardized features):")
    for f, c in zip(FEATURES, logreg.coef_[0]):
        p(f"  {f}: {c:.4f}")

    p("\n=== Decision Tree Classifier (max_depth=3) ===")
    tree = DecisionTreeClassifier(max_depth=3, random_state=42)
    tree.fit(X_train, y_train)
    pred_tree = tree.predict(X_test)
    acc_tree = accuracy_score(y_test, pred_tree)
    p(f"Test accuracy: {acc_tree:.3f}")
    p(f"Confusion matrix [[TN FP][FN TP]]:\n{confusion_matrix(y_test, pred_tree)}")
    p("Feature importances:")
    for f, imp in zip(FEATURES, tree.feature_importances_):
        p(f"  {f}: {imp:.4f}")

    baseline = max(y_test.mean(), 1 - y_test.mean())
    p(f"\nBaseline (always predict majority class): {baseline:.3f}")

    # keep the better-performing model as the deployed artifact
    best_name, best_model, best_acc = (
        ("logistic_regression", logreg, acc_lr) if acc_lr >= acc_tree
        else ("decision_tree", tree, acc_tree)
    )
    p(f"\nSelected model for deployment: {best_name} (test accuracy {best_acc:.3f})")

    joblib.dump(
        {"model": best_model, "scaler": scaler if best_name == "logistic_regression" else None,
         "features": FEATURES, "model_name": best_name},
        f"{OUT_DIR}/security_movement_model.pkl",
    )

    with open(f"{OUT_DIR}/ml_model_output.txt", "w") as f:
        f.write("\n".join(log))

    print("\nSaved model to security_movement_model.pkl and log to ml_model_output.txt")

if __name__ == "__main__":
    main()
