import os
from openai import OpenAI
from app.core.config import settings

_client: OpenAI = None

__all__ = ["get_client", "init_external_services"]

def get_client() -> OpenAI:
    """OpenAI clientを取得する。初期化されていない場合はエラーを発生させる。"""
    if _client is None:
        raise RuntimeError("OpenAI client is not initialized. Call init_external_services() first.")
    return _client

async def init_external_services():
    global _client

    # OpenAI client
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    _client = OpenAI(api_key=settings.openai_api_key)
    
    print("✅ OpenAI client initialized successfully")