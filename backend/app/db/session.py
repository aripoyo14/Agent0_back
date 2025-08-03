from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from typing import Generator

# すでにconfig.pyで定義済みのURLを使う
DATABASE_URL = settings.get_database_url()

# SSL付きでエンジンを作成
engine = create_engine(
    DATABASE_URL,
    connect_args={"ssl": {"ca": settings.get_ssl_ca_absolute_path()}},
    pool_pre_ping=True,
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
