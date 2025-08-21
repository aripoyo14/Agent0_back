# app/core/security/continuous_verification/config.py
"""
継続的検証の設定
環境変数による柔軟な設定とデフォルト値の提供
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class ContinuousVerificationConfig(BaseSettings):
    """継続的検証の設定クラス"""
    
    # 基本設定
    ENABLED: bool = True
    MONITORING_ONLY: bool = True  # 開発中は監視のみ
    
    # リスク閾値（段階的な制御）
    LOW_RISK_THRESHOLD: int = 30
    MEDIUM_RISK_THRESHOLD: int = 60
    HIGH_RISK_THRESHOLD: int = 80
    EXTREME_RISK_THRESHOLD: int = 95
    
    # パフォーマンス設定
    ASYNC_PROCESSING: bool = True
    PERFORMANCE_MODE: bool = True
    BATCH_SIZE: int = 100
    CLEANUP_INTERVAL_HOURS: int = 24
    
    # セキュリティ設定
    FAILSAFE_MODE: bool = True
    DEFAULT_ACTION: str = "ALLOW"
    MAX_SESSION_AGE_HOURS: int = 24
    
    # 監視設定
    BEHAVIOR_LEARNING_ENABLED: bool = True
    THREAT_DETECTION_ENABLED: bool = True
    RISK_SCORING_ENABLED: bool = True
    
    # ログ設定
    LOG_LEVEL: str = "INFO"
    LOG_DETAILED_BEHAVIOR: bool = False
    
    class Config:
        env_prefix = "CONTINUOUS_VERIFICATION_"
        extra = "ignore"
        case_sensitive = False

# グローバル設定インスタンス
config = ContinuousVerificationConfig()