"""
DB engine + session setup.

Defaults to SQLite (zero-config, works out of the box for local dev / demo).
Point DATABASE_URL at Postgres or MySQL for anything beyond a demo, e.g.:

    postgresql+psycopg2://user:password@localhost:5432/hcp_crm
    mysql+pymysql://user:password@localhost:3306/hcp_crm
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hcp_crm.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
