from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# プロジェクトルート基準の絶対パスを取得
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Database
    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=3306, alias="DATABASE_PORT")
    database_name: str = Field(default="agent0", alias="DATABASE_NAME")
    database_username: str = Field(default="students", alias="DATABASE_USERNAME")
    database_password: str = Field(default="password123", alias="DATABASE_PASSWORD")
    ssl_ca_path: str = Field(default="DigiCertGlobalRootCA.crt.pem", alias="DATABASE_SSL_CA_PATH")

    # 認証
    secret_key: str = Field(default="your-secret-key-here-make-it-long-and-secure", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # 外部API
    openai_api_key: str = Field(default="your-openai-api-key-here", alias="OPENAI_API_KEY")
    pinecone_api_key: str = Field(default="your-pinecone-api-key-here", alias="PINECONE_API_KEY")
    pinecone_env: str = Field(default="your-pinecone-environment-here", alias="PINECONE_ENVIRONMENT")
    pinecone_index: str = Field(default="your-pinecone-index-here", alias="PINECONE_INDEX")

    model_config = SettingsConfigDict(
        env_file=".env",  # プロジェクトルートにある.envファイルを指定
        extra="ignore"    # 不要な.env項目は無視
    )

    def get_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.database_username}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    def get_ssl_ca_absolute_path(self) -> str:
        return str(Path(self.ssl_ca_path).resolve())

settings = Settings()

print("✅ Loaded settings:", settings.dict())

@lru_cache
def get_settings() -> Settings:
    return settings