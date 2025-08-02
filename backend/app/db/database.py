from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# データベース接続URLを設定
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:root@localhost/bbc_test"

# エンジン作成
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Baseクラスを作成
Base = declarative_base()

# テーブル作成（もしテーブルがまだない場合）
# Base.metadata.create_all(bind=engine)
