# Aditi Securities — Database Systems Course Project (CSCI-GA.2433-001, Summer 2026)

Aditi Rai (ar9598) — Instructor: Jean-Claude Franchitti

An investment/brokerage firm case study built across the four parts of the course project.

- **part1/** — Conceptual model: 20-entity ER diagram, `aditi_securities.sql` (logical schema), report.
- **part2/** — Hybrid data lake: real Yahoo Finance/SEC EDGAR data, `part2_schema_extension.sql`
  (LAKE_DOCUMENT, SECURITY_SIGNAL), reference architecture, report.
- **part3/** — Physical design: indexes/partitioning/materialization (`part3_physical_design.sql`),
  the first trained ML model (`train_ml_model.py`), use-case diagram, report.
- **part4/** — End-to-end application: `aditi_securities_app/` (Flask + SQLAlchemy ORM), the
  data-driven retraining pipeline, finalized reference architecture, report.

See `part4/aditi_securities_app/README.md` for how to run the end-to-end application.

## Deployment target

The application defaults to a local SQLite database for self-contained grading/demo purposes.
Parts 2–3 also deployed a real Azure Blob Storage data lake and (part 3) an Azure Database for
MySQL instance; the app's `DATABASE_URL` environment variable is a one-line switch between the two
(see `part4/aditi_securities_app/db.py`).
