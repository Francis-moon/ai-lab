from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///parking.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,   # True 会打印 SQL，初学时可改成 True 看执行过程
    future=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

Base = declarative_base()