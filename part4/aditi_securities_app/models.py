# Aditi Rai
# Aditi Securities - Project Part IV
# SQLAlchemy ORM models for the subset of the Part I/II/III schema needed by
# the quote/onboarding workflow application. Table and column names match
# aditi_securities.sql / part2_schema_extension.sql / part3_physical_design.sql
# exactly, so these models can be pointed at the real Azure MySQL database
# from Part III just by changing the DATABASE_URL (see db.py) -- no renaming
# needed. The remaining Part I tables not used by this workflow (FIRM,
# BRANCH, FINANCIAL_PROFESSIONAL, ORDERS, TRADE, COMMISSION, CLEARINGHOUSE,
# SETTLEMENT, COMPLIANCE_FLAG, APPOINTMENT, CLIENT_ADVISOR_ASSIGNMENT,
# PORTFOLIO_VALUATION) still live in aditi_securities.sql and can be mapped
# the same way if a later workflow needs them.

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Client(Base):
    __tablename__ = "CLIENT"
    Client_id = Column(Integer, primary_key=True, autoincrement=True)
    Fname = Column(String(50), nullable=False)
    Lname = Column(String(50), nullable=False)
    Email = Column(String(100))
    Phone = Column(String(20))
    Address = Column(String(200))
    Date_of_birth = Column(Date)
    Tax_id = Column(String(11), nullable=False, unique=True)

    accounts = relationship("Account", back_populates="client")


class RiskProfile(Base):
    __tablename__ = "RISK_PROFILE"
    Risk_profile_id = Column(Integer, primary_key=True, autoincrement=True)
    Risk_tolerance = Column(Enum("Conservative", "Moderate", "Aggressive", name="risk_tolerance_enum"), nullable=False)
    Investment_goal = Column(String(100), nullable=False)
    Time_horizon = Column(String(50))
    Review_date = Column(Date)

    accounts = relationship("Account", back_populates="risk_profile")


class Account(Base):
    __tablename__ = "ACCOUNT"
    Account_id = Column(Integer, primary_key=True, autoincrement=True)
    Client_id = Column(Integer, ForeignKey("CLIENT.Client_id"), nullable=False)
    Risk_profile_id = Column(Integer, ForeignKey("RISK_PROFILE.Risk_profile_id"), nullable=False)
    Account_type = Column(Enum("Individual", "Joint", "IRA", "Margin", "Trust", name="account_type_enum"), nullable=False)
    Open_date = Column(Date, nullable=False, default=datetime.utcnow)
    Status = Column(Enum("Active", "Frozen", "Closed", name="account_status_enum"), nullable=False, default="Active")
    Beneficiary_name = Column(String(100))
    Beneficiary_relationship = Column(String(50))

    client = relationship("Client", back_populates="accounts")
    risk_profile = relationship("RiskProfile", back_populates="accounts")
    portfolio = relationship("Portfolio", back_populates="account", uselist=False)


class Issuer(Base):
    __tablename__ = "ISSUER"
    Issuer_id = Column(Integer, primary_key=True, autoincrement=True)
    Issuer_name = Column(String(100), nullable=False)
    Country = Column(String(50))
    Credit_rating = Column(String(5))

    securities = relationship("Security", back_populates="issuer")


class SecurityType(Base):
    __tablename__ = "SECURITY_TYPE"
    Sec_type_id = Column(Integer, primary_key=True, autoincrement=True)
    Type_name = Column(String(50), nullable=False)
    Description = Column(String(200))

    securities = relationship("Security", back_populates="sec_type")


class Security(Base):
    __tablename__ = "SECURITY"
    Security_id = Column(Integer, primary_key=True, autoincrement=True)
    Ticker = Column(String(10), nullable=False)
    Sec_name = Column(String(100), nullable=False)
    Sec_type_id = Column(Integer, ForeignKey("SECURITY_TYPE.Sec_type_id"), nullable=False)
    Issuer_id = Column(Integer, ForeignKey("ISSUER.Issuer_id"), nullable=False)
    Exchange = Column(String(20))
    Currency = Column(String(3), nullable=False, default="USD")
    __table_args__ = (UniqueConstraint("Ticker", "Exchange", name="uq_security_ticker_exchange"),)

    issuer = relationship("Issuer", back_populates="securities")
    sec_type = relationship("SecurityType", back_populates="securities")
    holdings = relationship("Holding", back_populates="security")
    signals = relationship("SecuritySignal", back_populates="security")


class Portfolio(Base):
    __tablename__ = "PORTFOLIO"
    Portfolio_id = Column(Integer, primary_key=True, autoincrement=True)
    Account_id = Column(Integer, ForeignKey("ACCOUNT.Account_id"), nullable=False, unique=True)
    Inception_date = Column(Date, nullable=False, default=datetime.utcnow)
    Base_currency = Column(String(3), nullable=False, default="USD")

    account = relationship("Account", back_populates="portfolio")
    holdings = relationship("Holding", back_populates="portfolio")
    risk_summary = relationship("PortfolioRiskSummary", back_populates="portfolio")


class Holding(Base):
    __tablename__ = "HOLDING"
    Portfolio_id = Column(Integer, ForeignKey("PORTFOLIO.Portfolio_id"), primary_key=True)
    Security_id = Column(Integer, ForeignKey("SECURITY.Security_id"), primary_key=True)
    Quantity = Column(Numeric(15, 4), nullable=False)
    Cost_basis = Column(Numeric(15, 2), nullable=False)
    Last_updated = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")
    security = relationship("Security", back_populates="holdings")


class LakeDocument(Base):
    __tablename__ = "LAKE_DOCUMENT"
    Document_id = Column(Integer, primary_key=True, autoincrement=True)
    Security_id = Column(Integer, ForeignKey("SECURITY.Security_id"))
    Source = Column(String(100), nullable=False)
    Doc_type = Column(Enum("Price_history", "News", "Filing", "Other", name="doc_type_enum"), nullable=False)
    Content_format = Column(Enum("CSV", "JSON", "TXT", "HTML", "PDF", name="content_format_enum"), nullable=False)
    Storage_uri = Column(String(500), nullable=False, unique=True)
    Collected_date = Column(Date, nullable=False)
    Description = Column(String(300))

    signals = relationship("SecuritySignal", back_populates="document")


class SecuritySignal(Base):
    __tablename__ = "SECURITY_SIGNAL"
    Signal_id = Column(Integer, primary_key=True, autoincrement=True)
    Security_id = Column(Integer, ForeignKey("SECURITY.Security_id"), nullable=False)
    Document_id = Column(Integer, ForeignKey("LAKE_DOCUMENT.Document_id"), nullable=False)
    Signal_date = Column(Date, nullable=False)
    Signal_type = Column(String(50), nullable=False)
    Signal_value = Column(Numeric(12, 4), nullable=False)
    __table_args__ = (UniqueConstraint("Security_id", "Document_id", "Signal_date", "Signal_type", name="uq_signal"),)

    security = relationship("Security", back_populates="signals")
    document = relationship("LakeDocument", back_populates="signals")


class PortfolioRiskSummary(Base):
    """Materialized/denormalized rollup from Part III's physical design,
    extended in Part IV with the live ML model output (Predicted_up_probability,
    Model_version) so the OLTP schema reflects the machine learning insight,
    not just the raw signal aggregates."""
    __tablename__ = "PORTFOLIO_RISK_SUMMARY"
    Portfolio_id = Column(Integer, ForeignKey("PORTFOLIO.Portfolio_id"), primary_key=True)
    Security_id = Column(Integer, ForeignKey("SECURITY.Security_id"), primary_key=True)
    Quantity = Column(Numeric(15, 4), nullable=False)
    Latest_signal_date = Column(Date)
    News_sentiment = Column(Numeric(12, 4))
    Price_3mo_return = Column(Numeric(12, 4))
    Open_risk_mentions = Column(Integer, nullable=False, default=0)
    Predicted_up_probability = Column(Numeric(6, 4))
    Model_version = Column(String(40))
    Last_refreshed = Column(DateTime, nullable=False, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="risk_summary")
    security = relationship("Security")


class QuoteRequest(Base):
    """New in Part IV: every time a prospect/client requests an investment
    plan / quote through the workflow app, the request and the model-driven
    recommendation it received are written to the OLTP database -- this is
    the concrete instance of 'updating the OLTP/ODS database to consider
    insights obtained by applying a machine learning model' required by the
    Part IV spec."""
    __tablename__ = "QUOTE_REQUEST"
    Quote_id = Column(Integer, primary_key=True, autoincrement=True)
    Requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    Prospect_name = Column(String(100), nullable=False)
    Risk_tolerance = Column(Enum("Conservative", "Moderate", "Aggressive", name="quote_risk_enum"), nullable=False)
    Ticker = Column(String(10), nullable=False)
    Predicted_up_probability = Column(Numeric(6, 4))
    Model_version = Column(String(40))
    Recommendation_text = Column(String(500))
