from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from app.core.config import settings

# ロガーの設定
logger = logging.getLogger(__name__)

# DB URLとSSL証明書パスを取得
DATABASE_URL = settings.get_database_url()
SSL_CA_PATH = settings.get_ssl_ca_absolute_path()

# エンジン作成
if SSL_CA_PATH:
    # SSL証明書が存在する場合
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "ssl": {"ca": SSL_CA_PATH}
        }
    )
    logger.info(f"SSL証明書を使用してデータベースに接続: {SSL_CA_PATH}")
else:
    # SSL証明書が存在しない場合
    engine = create_engine(
        DATABASE_URL,
        connect_args={}
    )
    logger.warning("SSL証明書なしでデータベースに接続")

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Baseクラスを作成
Base = declarative_base()

# テーブル作成（もしテーブルがまだない場合）
# Base.metadata.create_all(bind=engine)
