# Aditi Rai
# Aditi Securities - Project Part IV
# End-to-end workflow-based database application. Implements the "Request
# Investment Plan / Quote" and "Review Security Risk Signals" use cases from
# the Part III use-case diagram, backed by the SQLAlchemy ORM models in
# models.py and the data-driven ML pipeline in ml_pipeline.py.

import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy.orm import joinedload

from db import init_db, get_session
from models import Security, Portfolio, Holding, PortfolioRiskSummary, QuoteRequest, Client, Account
import ml_pipeline as mlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "datalake")
MODEL_PATH = os.path.join(BASE_DIR, "security_movement_model.pkl")
STATE_PATH = os.path.join(BASE_DIR, "model_state.json")

app = Flask(__name__)
app.secret_key = "aditi-securities-dev-key"

init_db()


@app.route("/")
def home():
    session = get_session()
    securities = session.query(Security).all()
    # Eager-load Account.client with a single JOIN (joinedload) instead of
    # issuing one extra query per account when the template reads a.client
    # -- avoids the classic ORM N+1 query problem.
    accounts = session.query(Account).options(joinedload(Account.client)).all()
    model_version = None
    if os.path.exists(STATE_PATH):
        import json
        with open(STATE_PATH) as f:
            model_version = json.load(f).get("version")
    try:
        return render_template("home.html", securities=securities, accounts=accounts, model_version=model_version)
    finally:
        session.close()


@app.route("/quote", methods=["GET", "POST"])
def quote():
    session = get_session()
    securities = session.query(Security).all()
    result = None
    if request.method == "POST":
        name = request.form.get("name", "Prospect")
        risk_tolerance = request.form.get("risk_tolerance", "Moderate")
        ticker = request.form.get("ticker")

        # Data-driven step: check whether new price data has arrived since
        # the model was last trained, and retrain automatically if so --
        # this is what makes the same query return a different result over
        # time, per the Part IV / lecture requirement.
        retrained, bundle, feat_df = mlp.retrain_if_needed(session, DATA_DIR, MODEL_PATH, STATE_PATH)

        pred = mlp.predict_for_ticker(bundle, feat_df, ticker)
        prob_up, as_of = pred if pred else (None, None)

        if prob_up is None:
            recommendation = f"No recent price data available for {ticker} to generate a recommendation."
        elif prob_up >= 0.55:
            recommendation = (f"Model favors {ticker}: {prob_up:.1%} estimated probability of a positive "
                               f"move next session. Consistent with a {risk_tolerance.lower()} risk tolerance.")
        elif prob_up <= 0.45:
            recommendation = (f"Model is cautious on {ticker}: only {prob_up:.1%} estimated probability of a "
                               f"positive move next session. Consider a smaller position or a review.")
        else:
            recommendation = f"Model is neutral on {ticker} ({prob_up:.1%} estimated probability of a positive move)."

        # Update the OLTP database with this quote and the model's insight.
        qr = QuoteRequest(
            Requested_at=datetime.utcnow(), Prospect_name=name, Risk_tolerance=risk_tolerance,
            Ticker=ticker, Predicted_up_probability=prob_up, Model_version=bundle["version"],
            Recommendation_text=recommendation,
        )
        session.add(qr)
        session.commit()

        result = {
            "ticker": ticker, "probability_up": prob_up, "as_of": as_of,
            "recommendation": recommendation, "model_version": bundle["version"],
            "retrained_this_request": retrained, "quote_id": qr.Quote_id,
        }
    try:
        return render_template("quote.html", securities=securities, result=result)
    finally:
        session.close()


@app.route("/portfolio/<int:portfolio_id>")
def portfolio_view(portfolio_id):
    session = get_session()
    portfolio = session.get(Portfolio, portfolio_id)
    rows = []
    if portfolio:
        # Eager-load Holding.security so the template's h.security access
        # doesn't issue one query per holding.
        holdings = (session.query(Holding)
                    .options(joinedload(Holding.security))
                    .filter(Holding.Portfolio_id == portfolio_id).all())
        for h in holdings:
            summary = session.get(PortfolioRiskSummary, (h.Portfolio_id, h.Security_id))
            rows.append({"holding": h, "security": h.security, "summary": summary})
    try:
        return render_template("portfolio.html", portfolio=portfolio, rows=rows)
    finally:
        session.close()


@app.route("/admin/retrain", methods=["POST"])
def admin_retrain():
    session = get_session()
    retrained, bundle, feat_df = mlp.retrain_if_needed(session, DATA_DIR, MODEL_PATH, STATE_PATH, force=True)
    session.close()
    flash(f"Retrain complete. Model version {bundle['version']} "
          f"(test accuracy {bundle['test_accuracy']:.3f}, {bundle['n_rows']} training rows).")
    return redirect(url_for("home"))


@app.route("/quotes")
def quotes_log():
    session = get_session()
    quotes = session.query(QuoteRequest).order_by(QuoteRequest.Requested_at.desc()).limit(50).all()
    try:
        return render_template("quotes.html", quotes=quotes)
    finally:
        session.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
