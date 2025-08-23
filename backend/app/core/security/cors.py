from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

def get_cors_config():
    """CORS設定の詳細情報を取得（デバッグ用）"""
    settings = get_settings()
    
    return {
        "environment": settings.environment,
        "allow_origins": settings.get_cors_origins(),
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
        "max_age": settings.cors_max_age,
    }

def get_cors_middleware_config():
    """CORS設定の辞書を取得（FastAPIのadd_middleware用）"""
    settings = get_settings()
    
    return {
        "allow_origins": settings.get_cors_origins(),
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
        "max_age": settings.cors_max_age,
    }

def get_secure_cors_middleware_config():
    """セキュリティ強化されたCORS設定を取得"""
    settings = get_settings()
    
    # 本番環境ではより厳格な設定
    if settings.is_production:
        return {
            "allow_origins": settings.get_cors_origins(),
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],  # OPTIONSを除外
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
            ],  # 必要最小限のヘッダーのみ
            "max_age": 3600,  # 1時間
            "expose_headers": ["X-Total-Count"],  # 明示的に公開するヘッダー
        }
    
    # 開発環境では柔軟な設定
    return get_cors_middleware_config()
