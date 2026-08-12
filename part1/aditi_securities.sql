-- Aditi Rai
-- Aditi Securities - Logical schema (generated from the Part I conceptual model, MySQL target)
-- In MySQL Workbench: File > Import > Reverse Engineer MySQL Create Script to load this model.

CREATE DATABASE IF NOT EXISTS aditi_securities;
USE aditi_securities;

CREATE TABLE FIRM (
  Firm_id        INT           NOT NULL AUTO_INCREMENT,
  Firm_name      VARCHAR(100)  NOT NULL,
  Crd_number     VARCHAR(20)   NOT NULL,
  Address        VARCHAR(200),
  PRIMARY KEY (Firm_id),
  UNIQUE (Crd_number)
);

CREATE TABLE BRANCH (
  Branch_id      INT           NOT NULL AUTO_INCREMENT,
  Firm_id        INT           NOT NULL,
  Branch_name    VARCHAR(100)  NOT NULL,
  Address        VARCHAR(200),
  Phone          VARCHAR(20),
  PRIMARY KEY (Branch_id),
  FOREIGN KEY (Firm_id) REFERENCES FIRM(Firm_id)
);

CREATE TABLE CLIENT (
  Client_id      INT           NOT NULL AUTO_INCREMENT,
  Fname          VARCHAR(50)   NOT NULL,
  Lname          VARCHAR(50)   NOT NULL,
  Email          VARCHAR(100),
  Phone          VARCHAR(20),
  Address        VARCHAR(200),
  Date_of_birth  DATE,
  Tax_id         VARCHAR(11)   NOT NULL,
  PRIMARY KEY (Client_id),
  UNIQUE (Tax_id)
);

CREATE TABLE RISK_PROFILE (
  Risk_profile_id INT          NOT NULL AUTO_INCREMENT,
  Risk_tolerance  ENUM('Conservative','Moderate','Aggressive') NOT NULL,
  Investment_goal VARCHAR(100) NOT NULL,
  Time_horizon    VARCHAR(50),
  Review_date     DATE,
  PRIMARY KEY (Risk_profile_id)
);

CREATE TABLE ACCOUNT (
  Account_id      INT          NOT NULL AUTO_INCREMENT,
  Client_id       INT          NOT NULL,
  Risk_profile_id INT          NOT NULL,
  Account_type    ENUM('Individual','Joint','IRA','Margin','Trust') NOT NULL,
  Open_date       DATE         NOT NULL,
  Status          ENUM('Active','Frozen','Closed') NOT NULL DEFAULT 'Active',
  Beneficiary_name         VARCHAR(100),
  Beneficiary_relationship VARCHAR(50),
  PRIMARY KEY (Account_id),
  FOREIGN KEY (Client_id) REFERENCES CLIENT(Client_id),
  FOREIGN KEY (Risk_profile_id) REFERENCES RISK_PROFILE(Risk_profile_id)
);

CREATE TABLE FINANCIAL_PROFESSIONAL (
  Fp_id          INT           NOT NULL AUTO_INCREMENT,
  Fname          VARCHAR(50)   NOT NULL,
  Lname          VARCHAR(50)   NOT NULL,
  License_number VARCHAR(20)   NOT NULL,
  Email          VARCHAR(100),
  Firm_id        INT           NOT NULL,
  Branch_id      INT           NOT NULL,
  Hire_date      DATE,
  PRIMARY KEY (Fp_id),
  UNIQUE (License_number),
  FOREIGN KEY (Firm_id) REFERENCES FIRM(Firm_id),
  FOREIGN KEY (Branch_id) REFERENCES BRANCH(Branch_id)
);

CREATE TABLE CLIENT_ADVISOR_ASSIGNMENT (
  Client_id      INT           NOT NULL,
  Fp_id          INT           NOT NULL,
  Start_date     DATE          NOT NULL,
  End_date       DATE,
  Advisory_role  VARCHAR(50),
  PRIMARY KEY (Client_id, Fp_id, Start_date),
  FOREIGN KEY (Client_id) REFERENCES CLIENT(Client_id),
  FOREIGN KEY (Fp_id) REFERENCES FINANCIAL_PROFESSIONAL(Fp_id)
);

CREATE TABLE APPOINTMENT (
  Appointment_id INT           NOT NULL AUTO_INCREMENT,
  Client_id      INT           NOT NULL,
  Fp_id          INT           NOT NULL,
  Appt_datetime  DATETIME      NOT NULL,
  Purpose        VARCHAR(200),
  Status         ENUM('Scheduled','Completed','Cancelled') NOT NULL DEFAULT 'Scheduled',
  Notes          VARCHAR(500),
  PRIMARY KEY (Appointment_id),
  FOREIGN KEY (Client_id) REFERENCES CLIENT(Client_id),
  FOREIGN KEY (Fp_id) REFERENCES FINANCIAL_PROFESSIONAL(Fp_id)
);

CREATE TABLE ISSUER (
  Issuer_id      INT           NOT NULL AUTO_INCREMENT,
  Issuer_name    VARCHAR(100)  NOT NULL,
  Country        VARCHAR(50),
  Credit_rating  VARCHAR(5),
  PRIMARY KEY (Issuer_id)
);

CREATE TABLE SECURITY_TYPE (
  Sec_type_id    INT           NOT NULL AUTO_INCREMENT,
  Type_name      VARCHAR(50)   NOT NULL,
  Description    VARCHAR(200),
  PRIMARY KEY (Sec_type_id)
);

CREATE TABLE SECURITY (
  Security_id    INT           NOT NULL AUTO_INCREMENT,
  Ticker         VARCHAR(10)   NOT NULL,
  Sec_name       VARCHAR(100)  NOT NULL,
  Sec_type_id    INT           NOT NULL,
  Issuer_id      INT           NOT NULL,
  Exchange       VARCHAR(20),
  Currency       CHAR(3)       NOT NULL DEFAULT 'USD',
  PRIMARY KEY (Security_id),
  UNIQUE (Ticker, Exchange),
  FOREIGN KEY (Sec_type_id) REFERENCES SECURITY_TYPE(Sec_type_id),
  FOREIGN KEY (Issuer_id) REFERENCES ISSUER(Issuer_id)
);

CREATE TABLE ORDERS (
  Order_id       INT           NOT NULL AUTO_INCREMENT,
  Account_id     INT           NOT NULL,
  Security_id    INT           NOT NULL,
  Fp_id          INT,
  Order_type     ENUM('Market','Limit','Stop') NOT NULL,
  Side           ENUM('Buy','Sell')         NOT NULL,
  Quantity       DECIMAL(15,4) NOT NULL,
  Limit_price    DECIMAL(15,4),
  Order_datetime DATETIME      NOT NULL,
  Status         ENUM('Open','Filled','Cancelled','Rejected') NOT NULL DEFAULT 'Open',
  PRIMARY KEY (Order_id),
  CONSTRAINT fk_orders_account  FOREIGN KEY (Account_id) REFERENCES ACCOUNT(Account_id),
  CONSTRAINT fk_orders_security FOREIGN KEY (Security_id) REFERENCES SECURITY(Security_id),
  CONSTRAINT fk_orders_fp       FOREIGN KEY (Fp_id) REFERENCES FINANCIAL_PROFESSIONAL(Fp_id)
);

CREATE TABLE TRADE (
  Trade_id        INT           NOT NULL AUTO_INCREMENT,
  Order_id        INT           NOT NULL,
  Execution_price DECIMAL(15,4) NOT NULL,
  Execution_date  DATETIME      NOT NULL,
  Quantity_filled DECIMAL(15,4) NOT NULL,
  Venue           VARCHAR(50),
  PRIMARY KEY (Trade_id),
  CONSTRAINT fk_trade_order FOREIGN KEY (Order_id) REFERENCES ORDERS(Order_id)
);

CREATE TABLE COMMISSION (
  Commission_id  INT           NOT NULL AUTO_INCREMENT,
  Trade_id       INT           NOT NULL,
  Fp_id          INT           NOT NULL,
  Amount         DECIMAL(12,2) NOT NULL,
  Rate           DECIMAL(6,4),
  Pay_date       DATE,
  PRIMARY KEY (Commission_id),
  UNIQUE (Trade_id, Fp_id),
  FOREIGN KEY (Trade_id) REFERENCES TRADE(Trade_id),
  FOREIGN KEY (Fp_id) REFERENCES FINANCIAL_PROFESSIONAL(Fp_id)
);

CREATE TABLE PORTFOLIO (
  Portfolio_id   INT           NOT NULL AUTO_INCREMENT,
  Account_id     INT           NOT NULL,
  Inception_date DATE          NOT NULL,
  Base_currency  CHAR(3)       NOT NULL DEFAULT 'USD',
  PRIMARY KEY (Portfolio_id),
  UNIQUE (Account_id),
  FOREIGN KEY (Account_id) REFERENCES ACCOUNT(Account_id)
);

CREATE TABLE HOLDING (
  Portfolio_id   INT           NOT NULL,
  Security_id    INT           NOT NULL,
  Quantity       DECIMAL(15,4) NOT NULL,
  Cost_basis     DECIMAL(15,2) NOT NULL,
  Last_updated   DATETIME,
  PRIMARY KEY (Portfolio_id, Security_id),
  FOREIGN KEY (Portfolio_id) REFERENCES PORTFOLIO(Portfolio_id),
  FOREIGN KEY (Security_id) REFERENCES SECURITY(Security_id)
);

CREATE TABLE PORTFOLIO_VALUATION (
  Portfolio_id       INT           NOT NULL,
  Valuation_date     DATE          NOT NULL,
  Total_market_value DECIMAL(18,2) NOT NULL,
  Cash_balance       DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (Portfolio_id, Valuation_date),
  CONSTRAINT fk_valuation_portfolio FOREIGN KEY (Portfolio_id) REFERENCES PORTFOLIO(Portfolio_id)
);

CREATE TABLE COMPLIANCE_FLAG (
  Flag_id        INT           NOT NULL AUTO_INCREMENT,
  Account_id     INT           NOT NULL,
  Order_id       INT,
  Flag_type      VARCHAR(50)   NOT NULL,
  Raised_date    DATE          NOT NULL,
  Status         ENUM('Open','Under review','Resolved') NOT NULL DEFAULT 'Open',
  Resolution_date DATE,
  Reviewer       VARCHAR(100),
  PRIMARY KEY (Flag_id),
  CONSTRAINT fk_flag_account FOREIGN KEY (Account_id) REFERENCES ACCOUNT(Account_id),
  CONSTRAINT fk_flag_order   FOREIGN KEY (Order_id) REFERENCES ORDERS(Order_id)
);

CREATE TABLE CLEARINGHOUSE (
  Clearinghouse_id INT         NOT NULL AUTO_INCREMENT,
  Ch_name          VARCHAR(100) NOT NULL,
  Dtc_number       VARCHAR(20),
  PRIMARY KEY (Clearinghouse_id)
);

CREATE TABLE SETTLEMENT (
  Settlement_id    INT           NOT NULL AUTO_INCREMENT,
  Trade_id         INT           NOT NULL,
  Clearinghouse_id INT           NOT NULL,
  Settlement_date  DATE          NOT NULL,
  Settlement_status ENUM('Pending','Settled','Failed') NOT NULL DEFAULT 'Pending',
  Net_amount       DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (Settlement_id),
  UNIQUE (Trade_id),
  FOREIGN KEY (Trade_id) REFERENCES TRADE(Trade_id),
  FOREIGN KEY (Clearinghouse_id) REFERENCES CLEARINGHOUSE(Clearinghouse_id)
);
