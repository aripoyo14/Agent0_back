from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# DB URLとSSL証明書パスを取得
DATABASE_URL = settings.get_database_url()
SSL_CA_PATH = settings.get_ssl_ca_absolute_path()

# エンジン作成
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "ssl": {"ca": SSL_CA_PATH}
    }
)
print(SSL_CA_PATH)

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Baseクラスを作成
Base = declarative_base()

# テーブル作成（もしテーブルがまだない場合）
# Base.metadata.create_all(bind=engine)
