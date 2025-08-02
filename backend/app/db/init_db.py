from app.db.base import Base
from app.db.session import engine

def init_db():
    # 全テーブルを作成（存在しない場合のみ）
    Base.metadata.create_all(bind=engine)
