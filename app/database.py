"""SQLite setup and one-time loading of the simulated CSV dataset."""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = f"sqlite:///{ROOT / 'shipment_optimizer.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def initialise_database() -> None:
    """Create tables and seed them from CSV only when the database is empty."""
    from app.models import Route

    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        if session.query(Route).first() is not None:
            return
        frame = pd.read_csv(ROOT / "data" / "shipments.csv")
        routes = [Route(**row) for row in frame.to_dict(orient="records")]
        session.add_all(routes)
        session.commit()


def get_session():
    with SessionLocal() as session:
        yield session
