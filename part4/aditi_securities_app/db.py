# Aditi Rai
# Aditi Securities - Project Part IV
# Database connectivity. Defaults to a local SQLite file so the app is fully
# self-contained for grading/demo purposes; pointing this at the real Azure
# Database for MySQL instance from Part III is a one-line change (set the
# DATABASE_URL environment variable), since the SQLAlchemy models in
# models.py use the same table/column names as aditi_securities.sql,
# part2_schema_extension.sql, and part3_physical_design.sql.
#
# Example for the Part III Azure MySQL deployment:
#   export DATABASE_URL="mysql+pymysql://<user>:<password>@<azure-host>:3306/aditi_securities"

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_URL = "sqlite:///" + os.path.join(BASE_DIR, "aditi_securities.db")
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db():
    """Create all tables if they don't already exist (idempotent)."""
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
