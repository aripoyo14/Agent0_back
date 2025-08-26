# app/core/security/continuous_verification/config.py
"""
継続的検証システムの設定
"""
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from app.core.config import get_settings

class ContinuousVerificationConfig(BaseSettings):
    """継続的検証システムの設定クラス"""
    
    # 基本設定
    ENABLED: bool = True  # 本番環境では有効化
    ASYNC_PROCESSING: bool = True  # 非同期処理を有効化
    DEBUG_MODE: bool = True  # デバッグモードを有効化（問題解決後はFalseに戻す）
    
    # リスク閾値設定
    LOW_RISK_THRESHOLD: int = 30
    MEDIUM_RISK_THRESHOLD: int = 60
    HIGH_RISK_THRESHOLD: int = 80
    EXTREME_RISK_THRESHOLD: int = 90
    
    # 機能設定
    THREAT_DETECTION_ENABLED: bool = True
    BEHAVIOR_LEARNING_ENABLED: bool = True
    LOCATION_MONITORING_ENABLED: bool = True
    TIME_ANOMALY_DETECTION_ENABLED: bool = True
    
    # パフォーマンス設定
    CACHE_TTL_SECONDS: int = 300  # 5分
    MAX_SESSION_AGE_HOURS: int = 24
    BATCH_PROCESSING_SIZE: int = 100
    
    # 地理情報サービス設定
    GEOIP_SERVICE_ENABLED: bool = False  # 本番環境で必要に応じて有効化
    GEOIP_SERVICE_URL: Optional[str] = None
    GEOIP_API_KEY: Optional[str] = None
    
    # アラート設定
    SECURITY_ALERT_ENABLED: bool = True
    ALERT_EMAIL_ENABLED: bool = False
    ALERT_SLACK_ENABLED: bool = False
    ALERT_WEBHOOK_URL: Optional[str] = None
    
    # データ保持設定
    RISK_SCORE_RETENTION_DAYS: int = 90
    BEHAVIOR_PATTERN_RETENTION_DAYS: int = 180
    THREAT_DETECTION_RETENTION_DAYS: int = 365
    
    # メイン設定との連携
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        try:
            # メイン設定から継続的検証設定を取得
            main_settings = get_settings()
            cv_config = main_settings.get_continuous_verification_config()
            
            # メイン設定の値を優先
            self.ENABLED = cv_config.get("enabled", self.ENABLED)
            self.DEBUG_MODE = cv_config.get("log_level", "INFO") == "DEBUG"
            
            # 監視専用モードの設定
            if cv_config.get("monitoring_only", False):
                self.THREAT_DETECTION_ENABLED = False
                self.SECURITY_ALERT_ENABLED = False
            
            # フェイルセーフモードの設定
            if cv_config.get("failsafe_mode", False):
                self.EXTREME_RISK_THRESHOLD = 50  # より厳しい閾値
            
            # デフォルトアクションの設定
            default_action = cv_config.get("default_action", "DENY")
            if default_action == "ALLOW":
                self.EXTREME_RISK_THRESHOLD = 100  # 実質的に無効化
                
        except Exception as e:
            # メイン設定の取得に失敗した場合は、デフォルト値を使用
            logging.warning(f"メイン設定の取得に失敗: {e}")
            pass
        
        # ログレベルの設定
        if self.DEBUG_MODE:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
        else:
            logging.getLogger(__name__).setLevel(logging.INFO)
    
    class Config:
        env_prefix = "CV_"  # 環境変数のプレフィックス
        env_file = ".env"
        extra = "ignore"  # 未定義の環境変数は無視

# 設定インスタンス
config = ContinuousVerificationConfig()

# 設定の検証とログ出力
logging.info(f"継続的検証システム設定: enabled={config.ENABLED}, async={config.ASYNC_PROCESSING}")