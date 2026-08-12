Aditi Rai
Aditi Securities - Data Lake (Database Systems Project Part II, CSCI-GA.2433-001)

Structure:

  raw/       Datasets as collected from the source, unmodified.
    prices/    Daily price history (structured CSV) from Yahoo Finance for AAPL, MSFT, JPM,
               Apr 17 - Jul 15, 2026. Columns: Date, Open, High, Low, Close, AdjClose, Volume.
    news/      Market news headlines (unstructured JSON) from Yahoo Finance.
    filings/   SEC EDGAR filing text (unstructured). Contains the Risk Factors excerpt from
               Apple's 2025 Form 10-K.

  curated/   Data cleaned/derived from the raw zone, ready to load into the relational schema.
    security_signals.csv   Per-ticker signals derived from the raw documents (news sentiment,
                           risk-factor mentions, 3-month price return). Loads into the
                           SECURITY_SIGNAL table.

Every file in the lake is cataloged in the LAKE_DOCUMENT table of the relational schema
(see part2_schema_extension.sql), which links each document to the SECURITY it concerns.
