from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.core.config import settings


engine_kwargs = {"future": True, "pool_pre_ping": True}
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
