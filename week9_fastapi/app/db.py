from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./parking.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # FastAPI+SQLite的运行方式会线程切换,必须加
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()