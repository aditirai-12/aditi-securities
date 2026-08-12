# Aditi Securities — Project Part IV: End-to-End Workflow Application

Aditi Rai — CS-GA.2433-001 — Database Systems, Summer 2026

## What this is

A Flask + SQLAlchemy application implementing the "Request Investment Plan /
Quote" and portfolio risk review use cases from Part III, wired end-to-end to
the machine learning model trained on the Part II data lake. It satisfies the
Part IV requirement to update the OLTP/ODS database with insights from an ML
model, and to retrain that model automatically as the underlying unstructured
data (price history) changes.

## Structure

- `models.py` — SQLAlchemy ORM models. Table/column names match
  `aditi_securities.sql` / `part2_schema_extension.sql` /
  `part3_physical_design.sql` from Parts I–III, plus two new Part IV
  additions: `Predicted_up_probability`/`Model_version` on
  `PORTFOLIO_RISK_SUMMARY`, and the new `QUOTE_REQUEST` table.
- `db.py` — connection setup. Defaults to a local SQLite file; set
  `DATABASE_URL` to point at the Part III Azure MySQL instance instead
  (e.g. `mysql+pymysql://user:pass@host:3306/aditi_securities`) with no code
  changes.
- `seed.py` — seeds one client/account/portfolio with holdings in AAPL,
  MSFT, and JPM, and loads the Part II lake documents and curated signals.
- `ml_pipeline.py` — the data-driven module: trains/retrains the model from
  `datalake/raw/prices`, detects when the source data has changed
  (`should_retrain`), and refreshes `PORTFOLIO_RISK_SUMMARY` with the
  model's predictions.
- `app.py` — the Flask app: `/` (home), `/quote` (get a quote — triggers the
  data-driven retrain check on every request), `/portfolio/<id>` (holdings +
  risk summary), `/admin/retrain` (force a retrain), `/quotes` (OLTP log of
  every quote issued).
- `datalake/` — carried forward from Part II (raw prices/news/filings,
  curated signals).

## Running it

```
pip install -r requirements.txt
python3 seed.py        # one-time: creates and seeds the database
python3 app.py          # starts the app on http://127.0.0.1:5050
```

To point at the Azure MySQL database from Part III instead of local SQLite:

```
export DATABASE_URL="mysql+pymysql://<user>:<password>@<azure-host>:3306/aditi_securities"
python3 seed.py
python3 app.py
```

## Demonstrating the data-driven retraining

1. Visit `/quote`, request a quote for any ticker — note the model version
   and predicted probability.
2. Append a new row to one of the CSVs in `datalake/raw/prices/` (simulating
   a new day of unstructured price data arriving), or hit
   `/admin/retrain` to force it.
3. Request the same quote again — the model version and probability change,
   because the model was retrained on the updated data, with no manual step
   beyond making the new data available. This mirrors the example the
   instructor gave in class: the same query, run twice, returns a different
   answer because the underlying model changed.

## Query optimization notes

- `PORTFOLIO_RISK_SUMMARY` is a materialized/denormalized table (from Part
  III's physical design) so `/portfolio/<id>` is a single indexed lookup per
  holding instead of a live join across `HOLDING`, `SECURITY_SIGNAL`, and the
  ML model on every page view.
- SQLAlchemy relationships (`h.security`, `a.client`) are used instead of
  manual joins; for larger data this should be switched to eager loading
  (`joinedload`) to avoid N+1 queries when listing many holdings/accounts.
- All foreign keys used in these queries (`HOLDING.Security_id`,
  `PORTFOLIO_RISK_SUMMARY` primary key, `QUOTE_REQUEST.Ticker`) are indexed
  per the Part III physical design (`part3_physical_design.sql`).

## Relation to Parts I–III

- Part I: `aditi_securities.sql` (conceptual model / logical schema).
- Part II: `part2_schema_extension.sql`, `datalake/` (hybrid data lake).
- Part III: `part3_physical_design.sql` (indexes/partitioning/materialization),
  `train_ml_model.py` (the model this app's `ml_pipeline.py` productionizes).
- Part IV (this folder): the end-to-end application.
