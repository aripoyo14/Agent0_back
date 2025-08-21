# app/core/security/continuous_verification/config.py
"""
継続的検証の設定
環境変数による柔軟な設定とデフォルト値の提供
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pydantic import Field

class ContinuousVerificationConfig(BaseSettings):
    """継続的検証の設定クラス"""
    
    # 基本設定
    ENABLED: bool = Field(default=True, description="継続的検証を有効にするか")
    MONITORING_ONLY: bool = Field(default=False, description="監視のみモード")
    
    # リスク閾値
    LOW_RISK_THRESHOLD: int = Field(default=30, description="低リスク閾値")
    MEDIUM_RISK_THRESHOLD: int = Field(default=60, description="中リスク閾値")
    HIGH_RISK_THRESHOLD: int = Field(default=80, description="高リスク閾値")
    EXTREME_RISK_THRESHOLD: int = Field(default=95, description="極高リスク閾値")
    
    # パフォーマンス設定
    ASYNC_PROCESSING: bool = True
    PERFORMANCE_MODE: bool = True
    BATCH_SIZE: int = 100
    CLEANUP_INTERVAL_HOURS: int = 24
    
    # セキュリティ設定
    FAILSAFE_MODE: bool = Field(default=False, description="フェイルセーフモード")
    DEFAULT_ACTION: str = Field(default="DENY", description="デフォルトアクション")
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
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False

# グローバル設定インスタンス
config = ContinuousVerificationConfig()