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
    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")

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

    # CORS設定（文字列として受け取り、手動でパース）
    cors_allow_origins_str: str = Field(
        default="http://localhost:3000",
        alias="CORS_ALLOW_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods_str: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        alias="CORS_ALLOW_METHODS"
    )
    cors_allow_headers_str: str = Field(
        default="*",
        alias="CORS_ALLOW_HEADERS"
    )
    cors_max_age: int = Field(default=86400, alias="CORS_MAX_AGE")  # 24時間
    
    # 環境設定
    environment: str = Field(default="development", alias="ENVIRONMENT")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),  # 🔒 絶対パスを指定
        extra="ignore",  # 未定義の環境変数は無視
        env_parse_none_str=None,  # 空文字列をNoneとして扱う
        env_parse_json_values=True,  # JSON値を自動パース
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

    @property
    def is_production(self) -> bool:
        """本番環境かどうかを判定"""
        return self.environment.lower() in ["production", "prod"]
    
    @property
    def is_staging(self) -> bool:
        """ステージング環境かどうかを判定"""
        return self.environment.lower() in ["staging", "stg"]
    
    @property
    def is_development(self) -> bool:
        """開発環境かどうかを判定"""
        return self.environment.lower() in ["development", "dev"]
    
    @property
    def cors_allow_origins(self) -> list[str]:
        """CORSオリジンのリストを取得"""
        return [origin.strip() for origin in self.cors_allow_origins_str.split(",")]
    
    @property
    def cors_allow_methods(self) -> list[str]:
        """CORSメソッドのリストを取得"""
        return [method.strip() for method in self.cors_allow_methods_str.split(",")]
    
    @property
    def cors_allow_headers(self) -> list[str]:
        """CORSヘッダーのリストを取得"""
        if self.cors_allow_headers_str == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers_str.split(",")]
    
    def get_cors_origins(self) -> list[str]:
        """環境に応じたCORSオリジンを取得"""
        if self.is_production:
            # デバッグ用：環境変数の値をログ出力
            logger.info(f"本番環境 - cors_allow_origins_str: {self.cors_allow_origins_str}")
            logger.info(f"本番環境 - cors_allow_origins: {self.cors_allow_origins}")
            
            if self.cors_allow_origins_str and "localhost" not in self.cors_allow_origins_str:
                logger.info(f"環境変数を使用: {self.cors_allow_origins}")
                return self.cors_allow_origins
            else:
                logger.warning("本番環境でCORS_ALLOW_ORIGINSが設定されていません")
                # 一時的にフロントエンドのURLを許可
                return ["https://aps-agent0-02-afawambwf2bxd2fv.italynorth-01.azurewebsites.net"]
        elif self.is_staging:
            # ステージング環境
            return [
                "https://staging-your-app.azurewebsites.net",
                "http://localhost:3000",  # 開発者用
            ]
        else:
            # 開発環境
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",  # 別ポートも許可
            ]

settings = Settings()

logger.info("Loaded settings: %s", settings.dict())

@lru_cache
def get_settings() -> Settings:
    return settings