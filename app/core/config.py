from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=3306, alias="DATABASE_PORT")
    database_name: str = Field(default="agent0", alias="DATABASE_NAME")
    database_username: str = Field(default="students", alias="DATABASE_USERNAME")
    database_password: str = Field(default="password123", alias="DATABASE_PASSWORD")

    secret_key: str = Field(default="your-secret-key-here-make-it-long-and-secure", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(
        env_file=".env",  # プロジェクトルートにある.envファイルを指定
        extra="ignore"    # 不要な.env項目は無視
    )

settings = Settings()

print("✅ Loaded settings:", settings.dict())