-- Aditi Rai
-- Aditi Securities - Project Part II: logical schema extension
-- Adds the two tables that inter-relate the structured schema (Part I) with the
-- unstructured data lake. Run against the aditi_securities database from Part I,
-- or import into the MySQL Workbench model alongside the Part I tables.

USE aditi_securities;

-- Catalog of every object stored in the data lake. Each document is described by
-- metadata here (governance/metadata management) and optionally linked to the
-- SECURITY it concerns. Security_id is NULL for market-wide documents.
CREATE TABLE LAKE_DOCUMENT (
  Document_id    INT           NOT NULL AUTO_INCREMENT,
  Security_id    INT,
  Source         VARCHAR(100)  NOT NULL,   -- e.g., Yahoo Finance, SEC EDGAR
  Doc_type       ENUM('Price_history','News','Filing','Other') NOT NULL,
  Content_format ENUM('CSV','JSON','TXT','HTML','PDF') NOT NULL,
  Storage_uri    VARCHAR(500)  NOT NULL,   -- path/URI in the data lake (cloud blob)
  Collected_date DATE          NOT NULL,
  Description    VARCHAR(300),
  PRIMARY KEY (Document_id),
  UNIQUE (Storage_uri),
  FOREIGN KEY (Security_id) REFERENCES SECURITY(Security_id)
);

-- Insights derived from lake documents, expressed per security and date so they
-- can be joined against HOLDING, RISK_PROFILE, and COMPLIANCE_FLAG.
CREATE TABLE SECURITY_SIGNAL (
  Signal_id      INT           NOT NULL AUTO_INCREMENT,
  Security_id    INT           NOT NULL,
  Document_id    INT           NOT NULL,   -- lake document the signal was derived from
  Signal_date    DATE          NOT NULL,
  Signal_type    VARCHAR(50)   NOT NULL,   -- e.g., News_sentiment, Risk_mention, Price_3mo_return
  Signal_value   DECIMAL(12,4) NOT NULL,
  PRIMARY KEY (Signal_id),
  UNIQUE (Security_id, Document_id, Signal_date, Signal_type),
  CONSTRAINT fk_signal_security FOREIGN KEY (Security_id) REFERENCES SECURITY(Security_id),
  CONSTRAINT fk_signal_document FOREIGN KEY (Document_id) REFERENCES LAKE_DOCUMENT(Document_id)
);
