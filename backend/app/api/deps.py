from sqlalchemy.orm import Session
from app.db.database import SessionLocal

def get_db():
    """
    データベースセッションを取得する依存関係
    
    Yields:
        Session: SQLAlchemyセッション
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
