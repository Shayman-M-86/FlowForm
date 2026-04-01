from sqlalchemy.orm import sessionmaker

from app.db.base import CoreBase, ResponseBase
from app.db.engine import core_engine, response_engine

SessionLocal = sessionmaker()
SessionLocal.configure(
    binds={
        CoreBase: core_engine,
        ResponseBase: response_engine,
    }
)

session = SessionLocal()
