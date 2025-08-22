"""
監査ログの設定
"""
from pydantic_settings import BaseSettings


class AuditConfig(BaseSettings):
    """監査ログの設定"""
    
    # 監査ログの有効化
    AUDIT_ENABLED: bool = True
    
    # ログレベル
    AUDIT_LOG_LEVEL: str = "INFO"
    
    # 保持期間（日数）
    AUDIT_RETENTION_DAYS: int = 365
    
    # 機密情報のマスキング
    AUDIT_MASK_SENSITIVE: bool = True
    
    # リアルタイムアラート
    AUDIT_REALTIME_ALERTS: bool = False
    
    class Config:
        env_prefix = "AUDIT_"
        extra = "ignore"


# 設定インスタンスを作成
audit_config = AuditConfig()
