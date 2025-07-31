from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    database_host: str = Field(..., alias="DATABASE_HOST")
    database_port: int = Field(..., alias="DATABASE_PORT")
    database_name: str = Field(..., alias="DATABASE_NAME")
    database_username: str = Field(..., alias="DATABASE_USERNAME")
    database_password: str = Field(..., alias="DATABASE_PASSWORD")

    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field(..., alias="ALGORITHM")
    access_token_expire_minutes: int = Field(..., alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(
        env_file=".env",  # プロジェクトルートにある.envファイルを指定
        extra="ignore"    # 不要な.env項目は無視
    )

settings = Settings()

print("✅ Loaded settings:", settings.dict())