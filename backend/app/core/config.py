from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os
import logging
from pathlib import Path

# ロガーの設定
logger = logging.getLogger(__name__)

load_dotenv()

# プロジェクトルート基準の絶対パスを取得
# このファイルは `backend/backend/app/core/config.py` 配下にあるため、
# プロジェクトルートは2つ上の親ディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent

# .envファイルの絶対パスを明示的に設定
ENV_FILE_PATH = BASE_DIR.parent / ".env"

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
    
    # 暗号化
    encryption_key: str = Field(default="Q1VxcEVvTlRfN3FJSU13ZGNUckxwTUFtTVVVVk11Ni04M2tmQ2o0WGQ1bz0", alias="ENCRYPTION_KEY")

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

    # 継続的検証システム設定
    continuous_verification_enabled: bool = Field(default=True, alias="CONTINUOUS_VERIFICATION_ENABLED")
    continuous_verification_monitoring_only: bool = Field(default=False, alias="CONTINUOUS_VERIFICATION_MONITORING_ONLY")
    continuous_verification_failsafe_mode: bool = Field(default=False, alias="CONTINUOUS_VERIFICATION_FAILSAFE_MODE")
    continuous_verification_default_action: str = Field(default="DENY", alias="CONTINUOUS_VERIFICATION_DEFAULT_ACTION")
    continuous_verification_log_level: str = Field(default="INFO", alias="CONTINUOUS_VERIFICATION_LOG_LEVEL")

    # 追加の設定項目（エラーログで不足していた項目）
    # これらは環境変数に存在するが、設定クラスで定義されていなかった項目
    cosmos_connection_string_legacy: str = Field(default="", alias="COSMOS_CONNECTION_STRING_LEGACY")
    azure_blob_container_legacy: str = Field(default="", alias="AZURE_BLOB_CONTAINER_LEGACY")
    encryption_key_legacy: str = Field(default="", alias="ENCRYPTION_KEY_LEGACY")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),  # 🔒 絶対パスを指定
        extra="ignore"  # 未定義の環境変数は無視
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
            logger.info("SSL証明書パスが設定されていません")
            return None
            
        ssl_path = Path(self.ssl_ca_path)
        
        # 相対パスの場合、プロジェクトルートからの絶対パスに変換
        # `BASE_DIR` は `backend/backend/app` を指すため、プロジェクトルートは `BASE_DIR.parent.parent`
        if not ssl_path.is_absolute():
            ssl_path = BASE_DIR.parent.parent / self.ssl_ca_path
        
        # ファイルが存在するかチェック
        if ssl_path.exists():
            logger.info(f"SSL証明書ファイルが見つかりました: {ssl_path}")
            return str(ssl_path.resolve())
        else:
            logger.warning(f"SSL証明書ファイルが見つかりません: {ssl_path}")
            logger.warning(f"期待される場所: {ssl_path.absolute()}")
            return None

    def get_continuous_verification_config(self) -> dict:
        """継続的検証システムの設定を取得"""
        return {
            "enabled": self.continuous_verification_enabled,
            "monitoring_only": self.continuous_verification_monitoring_only,
            "failsafe_mode": self.continuous_verification_failsafe_mode,
            "default_action": self.continuous_verification_default_action,
            "log_level": self.continuous_verification_log_level
        }

    def get_cosmos_config(self) -> dict:
        """Cosmos DB設定を取得"""
        return {
            "connection_string": self.cosmos_connection_string or self.cosmos_connection_string_legacy,
            "database_name": self.cosmos_database_name,
            "collection_name": self.cosmos_collection_name
        }

    def get_azure_storage_config(self) -> dict:
        """Azure Blob Storage設定を取得"""
        return {
            "connection_string": self.azure_storage_connection_string,
            "container": self.azure_blob_container or self.azure_blob_container_legacy,
            "meeting_container": self.azure_meeting_container
        }

    def get_encryption_config(self) -> dict:
        """暗号化設定を取得"""
        return {
            "key": self.encryption_key or self.encryption_key_legacy
        }

settings = Settings()

logger.info("Loaded settings: %s", settings.dict())

@lru_cache
def get_settings() -> Settings:
    return settings