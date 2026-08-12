# Aditi Rai
# Aditi Securities - Project Part IV
# Seeds the database with representative data consistent with the Part I/II
# entities and the Part II data lake (AAPL, MSFT, JPM), so the workflow app
# has real accounts/holdings to demonstrate against. Safe to re-run: it
# checks for existing rows before inserting.

import csv
import datetime
import os

from db import init_db, get_session
from models import (
    Client, RiskProfile, Account, Issuer, SecurityType, Security,
    Portfolio, Holding, LakeDocument, SecuritySignal,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATALAKE = os.path.join(BASE_DIR, "datalake")

TICKERS = [
    ("AAPL", "Apple Inc.", "Apple Inc.", "US", "AA+"),
    ("MSFT", "Microsoft Corporation", "Microsoft Corporation", "US", "AAA"),
    ("JPM", "JPMorgan Chase & Co.", "JPMorgan Chase & Co.", "US", "A+"),
]


def seed():
    init_db()
    session = get_session()

    if session.query(Client).count() > 0:
        print("Database already seeded, skipping.")
        session.close()
        return

    client = Client(
        Fname="Jordan", Lname="Reyes", Email="jordan.reyes@example.com",
        Phone="555-0142", Address="88 West St, New York, NY",
        Date_of_birth=datetime.date(1985, 3, 14), Tax_id="123-45-6789",
    )
    session.add(client)

    risk_profile = RiskProfile(
        Risk_tolerance="Moderate", Investment_goal="Long-term growth",
        Time_horizon="10+ years", Review_date=datetime.date(2026, 1, 1),
    )
    session.add(risk_profile)
    session.flush()

    account = Account(
        Client_id=client.Client_id, Risk_profile_id=risk_profile.Risk_profile_id,
        Account_type="Individual", Open_date=datetime.date(2025, 6, 1), Status="Active",
    )
    session.add(account)
    session.flush()

    portfolio = Portfolio(Account_id=account.Account_id, Inception_date=datetime.date(2025, 6, 1), Base_currency="USD")
    session.add(portfolio)
    session.flush()

    equity_type = SecurityType(Type_name="Equity", Description="Common stock")
    session.add(equity_type)
    session.flush()

    securities = {}
    for ticker, sec_name, issuer_name, country, rating in TICKERS:
        issuer = Issuer(Issuer_name=issuer_name, Country=country, Credit_rating=rating)
        session.add(issuer)
        session.flush()
        sec = Security(Ticker=ticker, Sec_name=sec_name, Sec_type_id=equity_type.Sec_type_id,
                        Issuer_id=issuer.Issuer_id, Exchange="NASDAQ" if ticker != "JPM" else "NYSE", Currency="USD")
        session.add(sec)
        session.flush()
        securities[ticker] = sec

    # representative holdings for the seeded client's portfolio
    holdings_qty = {"AAPL": 150, "MSFT": 80, "JPM": 120}
    holdings_cost = {"AAPL": 24500.00, "MSFT": 21000.00, "JPM": 18000.00}
    for ticker, sec in securities.items():
        session.add(Holding(
            Portfolio_id=portfolio.Portfolio_id, Security_id=sec.Security_id,
            Quantity=holdings_qty[ticker], Cost_basis=holdings_cost[ticker],
            Last_updated=datetime.datetime.utcnow(),
        ))

    # catalog the raw lake documents (mirrors Part II's LAKE_DOCUMENT rows)
    doc_specs = [
        ("AAPL", "Yahoo Finance", "Price_history", "CSV",
         "raw/prices/AAPL_daily_2026-04-17_2026-07-15.csv", "Daily OHLCV history"),
        ("MSFT", "Yahoo Finance", "Price_history", "CSV",
         "raw/prices/MSFT_daily_2026-04-17_2026-07-15.csv", "Daily OHLCV history"),
        ("JPM", "Yahoo Finance", "Price_history", "CSV",
         "raw/prices/JPM_daily_2026-04-17_2026-07-15.csv", "Daily OHLCV history"),
        ("AAPL", "Yahoo Finance", "News", "JSON",
         "raw/news/AAPL_news_headlines_2026-07-22.json", "News headlines"),
        ("AAPL", "SEC EDGAR", "Filing", "TXT",
         "raw/filings/AAPL_10K_2025_Item1A_RiskFactors_excerpt.txt", "10-K Item 1A Risk Factors"),
    ]
    documents = {}
    for ticker, source, doc_type, fmt, uri, desc in doc_specs:
        doc = LakeDocument(Security_id=securities[ticker].Security_id, Source=source, Doc_type=doc_type,
                            Content_format=fmt, Storage_uri=uri, Collected_date=datetime.date(2026, 7, 22),
                            Description=desc)
        session.add(doc)
        session.flush()
        documents.setdefault(ticker, []).append(doc)

    # load the curated signals csv from Part II into SECURITY_SIGNAL
    curated_csv = os.path.join(DATALAKE, "curated", "security_signals.csv")
    with open(curated_csv) as f:
        for row in csv.DictReader(f):
            ticker = row["Ticker"]
            sec = securities.get(ticker)
            if not sec:
                continue
            doc_list = documents.get(ticker, [])
            doc = doc_list[0] if doc_list else None
            if doc is None:
                continue
            session.add(SecuritySignal(
                Security_id=sec.Security_id, Document_id=doc.Document_id,
                Signal_date=datetime.datetime.strptime(row["Signal_date"], "%Y-%m-%d").date(),
                Signal_type=row["Signal_type"], Signal_value=float(row["Signal_value"]),
            ))

    session.commit()
    print(f"Seeded client {client.Fname} {client.Lname} (Client_id={client.Client_id}), "
          f"account {account.Account_id}, portfolio {portfolio.Portfolio_id}, "
          f"{len(securities)} securities, holdings, lake documents, and signals.")
    session.close()


if __name__ == "__main__":
    seed()
