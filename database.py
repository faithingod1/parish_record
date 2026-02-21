from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./church_records.db"

# check_same_thread=False allows SQLite usage across FastAPI request threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a DB session per request and ensure it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
