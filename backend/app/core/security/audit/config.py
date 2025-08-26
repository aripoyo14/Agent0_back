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
    
    # 主要API監査の設定
    # 検索・分析系API - 機密情報へのアクセス追跡
    AUDIT_SEARCH_ANALYSIS_ENABLED: bool = True
    AUDIT_SEARCH_ANALYSIS_ALERT_THRESHOLD: int = 100  # 1時間あたりのアクセス数閾値
    
    # データ読み取り系API - 情報漏洩の追跡
    AUDIT_DATA_READ_ENABLED: bool = True
    AUDIT_DATA_READ_ALERT_THRESHOLD: int = 50  # 1時間あたりのアクセス数閾値
    
    # 権限変更系API - セキュリティ侵害の追跡
    AUDIT_PERMISSION_CHANGES_ENABLED: bool = True
    AUDIT_PERMISSION_CHANGES_ALERT_THRESHOLD: int = 10  # 1時間あたりの変更数閾値
    
    # 監査ログの詳細レベル
    AUDIT_DETAIL_LEVEL: str = "standard"  # minimal, standard, detailed
    
    # セッション追跡の有効化
    AUDIT_SESSION_TRACKING_ENABLED: bool = True
    
    # IPアドレス追跡の有効化
    AUDIT_IP_TRACKING_ENABLED: bool = True
    
    # ユーザーエージェント追跡の有効化
    AUDIT_USER_AGENT_TRACKING_ENABLED: bool = True
    
    class Config:
        env_prefix = "AUDIT_"
        extra = "ignore"


# 設定インスタンスを作成
audit_config = AuditConfig()
