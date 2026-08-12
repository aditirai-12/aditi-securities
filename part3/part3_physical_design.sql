-- Aditi Rai
-- Aditi Securities - Project Part III: Physical Database Design
-- Run against the aditi_securities database created in Part I/II
-- (aditi_securities.sql + part2_schema_extension.sql must already be applied).

USE aditi_securities;

-- =========================================================================
-- 1. INDEXING
-- Secondary indexes on foreign keys and columns that drive the firm's most
-- frequent lookups (documented in the Part III report, Section 2).
-- =========================================================================

-- Trading desk / client service: look up an account's order history, or all
-- orders on a given security, quickly instead of scanning ORDERS.
CREATE INDEX idx_orders_account        ON ORDERS (Account_id);
CREATE INDEX idx_orders_security_date  ON ORDERS (Security_id, Order_datetime);

-- Settlement/back-office: trades by execution date (end-of-day reconciliation).
CREATE INDEX idx_trade_exec_date       ON TRADE (Execution_date);

-- "Which portfolios hold security X" is needed whenever a new SECURITY_SIGNAL
-- comes in and compliance needs to know who is exposed to it.
CREATE INDEX idx_holding_security      ON HOLDING (Security_id);

-- Advisory desk: an FP's book of business and appointment history
-- (Part I report, Section 6: "Get Book" / "Get Last Touch" use cases).
CREATE INDEX idx_caa_fp                ON CLIENT_ADVISOR_ASSIGNMENT (Fp_id);
CREATE INDEX idx_appointment_fp_date   ON APPOINTMENT (Fp_id, Appt_datetime);

-- Compliance dashboard: open flags per account.
CREATE INDEX idx_compliance_status     ON COMPLIANCE_FLAG (Account_id, Status);

-- Signal lookups by type across securities (e.g., "all News_sentiment signals
-- this week" for a daily risk digest); Security_id/Signal_date are already
-- covered by the Part II unique key, this adds the Signal_type access path.
CREATE INDEX idx_signal_type_date      ON SECURITY_SIGNAL (Signal_type, Signal_date);

-- =========================================================================
-- 2. PARTITIONING
-- ORDERS, SECURITY_SIGNAL, and PORTFOLIO_VALUATION are the three tables that
-- grow without bound (new rows every trading day / every ETL run) while
-- almost every query on them filters by a recent date range. Range
-- partitioning by year lets MySQL prune whole partitions instead of
-- scanning the full table, and lets old partitions be archived independently.
--
-- MySQL requires every unique key (including the primary key) on a
-- partitioned table to contain the partitioning column. ORDERS and
-- SECURITY_SIGNAL therefore have their primary key widened to include the
-- date column; the surrogate key (Order_id / Signal_id) still comes from
-- AUTO_INCREMENT, so uniqueness in practice is unaffected. PORTFOLIO_VALUATION
-- already has a composite key that includes Valuation_date, so it needs no
-- change.
--
-- InnoDB also does not support foreign key constraints on a partitioned
-- table (MySQL error 1506), confirmed when this script was actually run
-- against a live server. This applies both to FKs a partitioned table
-- declares itself AND to FKs that other tables hold pointing into it
-- (TRADE.Order_id and COMPLIANCE_FLAG.Order_id both reference ORDERS, and
-- had to be dropped too once that surfaced against the live server). This
-- is a genuine, well-documented physical-design trade-off, not a
-- workaround: high-volume partitioned "fact" tables in production systems
-- commonly drop DB-enforced FK constraints in exchange for partition-
-- pruning performance, and enforce referential integrity in the
-- application/ETL layer instead (which already validates Account_id,
-- Security_id, etc. before insert). All affected FK constraints are
-- therefore dropped immediately before each table is partitioned.
-- =========================================================================

ALTER TABLE TRADE
  DROP FOREIGN KEY fk_trade_order;

ALTER TABLE COMPLIANCE_FLAG
  DROP FOREIGN KEY fk_flag_order;

ALTER TABLE ORDERS
  DROP FOREIGN KEY fk_orders_account,
  DROP FOREIGN KEY fk_orders_security,
  DROP FOREIGN KEY fk_orders_fp;

ALTER TABLE ORDERS
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (Order_id, Order_datetime);

ALTER TABLE ORDERS
  PARTITION BY RANGE (YEAR(Order_datetime)) (
    PARTITION p_2025_and_before VALUES LESS THAN (2026),
    PARTITION p_2026 VALUES LESS THAN (2027),
    PARTITION p_2027 VALUES LESS THAN (2028),
    PARTITION p_future VALUES LESS THAN MAXVALUE
  );

ALTER TABLE SECURITY_SIGNAL
  DROP FOREIGN KEY fk_signal_security,
  DROP FOREIGN KEY fk_signal_document;

ALTER TABLE SECURITY_SIGNAL
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (Signal_id, Signal_date);

ALTER TABLE SECURITY_SIGNAL
  PARTITION BY RANGE (YEAR(Signal_date)) (
    PARTITION p_2025_and_before VALUES LESS THAN (2026),
    PARTITION p_2026 VALUES LESS THAN (2027),
    PARTITION p_2027 VALUES LESS THAN (2028),
    PARTITION p_future VALUES LESS THAN MAXVALUE
  );

ALTER TABLE PORTFOLIO_VALUATION
  DROP FOREIGN KEY fk_valuation_portfolio;

ALTER TABLE PORTFOLIO_VALUATION
  PARTITION BY RANGE (YEAR(Valuation_date)) (
    PARTITION p_2025_and_before VALUES LESS THAN (2026),
    PARTITION p_2026 VALUES LESS THAN (2027),
    PARTITION p_2027 VALUES LESS THAN (2028),
    PARTITION p_future VALUES LESS THAN MAXVALUE
  );

-- =========================================================================
-- 3. CLUSTERING
-- InnoDB always clusters a table's data pages on its primary key, so the
-- clustering decision is really the choice of primary key. All high-insert-
-- rate tables (ORDERS, TRADE, SECURITY_SIGNAL, APPOINTMENT) intentionally
-- use an AUTO_INCREMENT surrogate key rather than a natural key such as
-- Ssn or Ticker: new rows are always appended at the end of the clustered
-- index, avoiding the random-page inserts and page splits that would happen
-- if rows clustered on a natural key were inserted out of order. Lookup
-- tables that are read far more often than written (SECURITY, ISSUER,
-- SECURITY_TYPE) keep small surrogate keys too, but their alternate keys
-- (Ticker/Exchange, License_number, Crd_number) are supported by the UNIQUE
-- constraints already defined in the Part I/II schema, which MySQL
-- implements as secondary indexes on the same clustered table.
-- =========================================================================

-- =========================================================================
-- 4. SELECTIVE MATERIALIZATION
-- The compliance/advisory workflow repeatedly needs "for every holding,
-- what is the most recent risk signal on that security" -- a join across
-- HOLDING, SECURITY_SIGNAL, and SECURITY that is too expensive to compute
-- on demand once SECURITY_SIGNAL has years of partitioned history. This
-- summary table materializes that join, refreshed by the ETL job that also
-- loads new signals (Part II, Section 3, Step 2/3).
-- =========================================================================

CREATE TABLE PORTFOLIO_RISK_SUMMARY (
  Portfolio_id        INT           NOT NULL,
  Security_id         INT           NOT NULL,
  Quantity             DECIMAL(15,4) NOT NULL,
  Latest_signal_date   DATE,
  News_sentiment       DECIMAL(12,4),
  Price_3mo_return     DECIMAL(12,4),
  Open_risk_mentions   INT           NOT NULL DEFAULT 0,
  Last_refreshed       DATETIME      NOT NULL,
  PRIMARY KEY (Portfolio_id, Security_id),
  FOREIGN KEY (Portfolio_id) REFERENCES PORTFOLIO(Portfolio_id),
  FOREIGN KEY (Security_id) REFERENCES SECURITY(Security_id)
);

-- Refresh statement run by the nightly ETL job after new signals land
-- (idempotent: reruns simply overwrite each portfolio/security row).
INSERT INTO PORTFOLIO_RISK_SUMMARY
  (Portfolio_id, Security_id, Quantity, Latest_signal_date,
   News_sentiment, Price_3mo_return, Open_risk_mentions, Last_refreshed)
SELECT
  h.Portfolio_id,
  h.Security_id,
  h.Quantity,
  MAX(s.Signal_date) AS Latest_signal_date,
  MAX(CASE WHEN s.Signal_type = 'News_sentiment' THEN s.Signal_value END) AS News_sentiment,
  MAX(CASE WHEN s.Signal_type = 'Price_3mo_return' THEN s.Signal_value END) AS Price_3mo_return,
  SUM(CASE WHEN s.Signal_type LIKE 'Risk_mention%' THEN 1 ELSE 0 END) AS Open_risk_mentions,
  NOW()
FROM HOLDING h
LEFT JOIN SECURITY_SIGNAL s ON s.Security_id = h.Security_id
GROUP BY h.Portfolio_id, h.Security_id
ON DUPLICATE KEY UPDATE
  Quantity = VALUES(Quantity),
  Latest_signal_date = VALUES(Latest_signal_date),
  News_sentiment = VALUES(News_sentiment),
  Price_3mo_return = VALUES(Price_3mo_return),
  Open_risk_mentions = VALUES(Open_risk_mentions),
  Last_refreshed = VALUES(Last_refreshed);
