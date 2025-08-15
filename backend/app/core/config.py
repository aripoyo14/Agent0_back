from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# プロジェクトルート基準の絶対パスを取得
# このファイルは `backend/backend/app/core/config.py` 配下にあるため、
# プロジェクトルートは2つ上の親ディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Database
    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=3306, alias="DATABASE_PORT")
    database_name: str = Field(default="agent0", alias="DATABASE_NAME")
    database_username: str = Field(default="students", alias="DATABASE_USERNAME")
    database_password: str = Field(default="password123", alias="DATABASE_PASSWORD")
    ssl_ca_path: str = Field(default="", alias="DATABASE_SSL_CA_PATH")

    # 認証
    secret_key: str = Field(default="your-secret-key-here-make-it-long-and-secure", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # 外部API
    openai_api_key: str = Field(default="your-openai-api-key-here", alias="OPENAI_API_KEY")
    # Google Programmable Search (Custom Search JSON API)
    google_cse_api_key: str = Field(default="", alias="GOOGLE_CSE_API_KEY")
    google_cse_cx: str = Field(default="", alias="GOOGLE_CSE_CX")
    google_cse_endpoint: str = Field(default="https://www.googleapis.com/customsearch/v1", alias="GOOGLE_CSE_ENDPOINT")

    # Azure Cosmos DB for MongoDB vCore
    cosmos_connection_string: str = Field(default="", alias="COSMOS_CONNECTION_STRING")
    cosmos_database_name: str = Field(default="vector_db", alias="COSMOS_DATABASE_NAME")
    cosmos_collection_name: str = Field(default="vectors", alias="COSMOS_COLLECTION_NAME")

    # Azure Blob Storage
    azure_storage_connection_string: str = Field(default="", alias="AZURE_STORAGE_CONNECTION_STRING")
    azure_blob_container: str = Field(default="default-container", alias="AZURE_BLOB_CONTAINER")
    azure_meeting_container: str = Field(default="meetings-minutes", alias="AZURE_MEETING_CONTAINER")

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
        """SSL証明書の絶対パスを取得する。ファイルが存在しない場合はNoneを返す"""
        # SSL証明書パスが空の場合はNoneを返す
        if not self.ssl_ca_path:
            print("ℹ️  SSL証明書パスが設定されていません")
            return None
            
        ssl_path = Path(self.ssl_ca_path)
        
        # 相対パスの場合、プロジェクトルートからの絶対パスに変換
        # `BASE_DIR` は `backend/backend/app` を指すため、プロジェクトルートは `BASE_DIR.parent.parent`
        if not ssl_path.is_absolute():
            ssl_path = BASE_DIR.parent.parent / self.ssl_ca_path
        
        # ファイルが存在するかチェック
        if ssl_path.exists():
            print(f"✅ SSL証明書ファイルが見つかりました: {ssl_path}")
            return str(ssl_path.resolve())
        else:
            print(f"⚠️  SSL証明書ファイルが見つかりません: {ssl_path}")
            print(f"   期待される場所: {ssl_path.absolute()}")
            return None

settings = Settings()

print("✅ Loaded settings:", settings.dict())

@lru_cache
def get_settings() -> Settings:
    return settings