"""
レート制限のデータモデル
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RateLimitType(str, Enum):
    """レート制限のタイプ"""
    IP = "ip"
    ENDPOINT = "endpoint"
    USER = "user"
    GLOBAL = "global"

class RateLimitRule(BaseModel):
    """レート制限ルール"""
    
    name: str = Field(description="ルール名")
    max_requests: int = Field(description="最大リクエスト数")
    window_seconds: int = Field(description="時間枠（秒）")
    request_type: RateLimitType = Field(description="制限タイプ")
    endpoint_pattern: Optional[str] = Field(default=None, description="エンドポイントパターン（ワイルドカード対応）")
    error_message: Optional[str] = Field(default=None, description="カスタムエラーメッセージ")
    enabled: bool = Field(default=True, description="ルールを有効にするか")
    
    class Config:
        """Pydantic設定"""
        use_enum_values = True

class RateLimitViolation(BaseModel):
    """レート制限違反の記録"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="違反発生時刻")
    identifier: str = Field(description="制限対象の識別子（IP、ユーザーID、エンドポイント）")
    request_type: RateLimitType = Field(description="制限タイプ")
    rule_name: str = Field(description="違反したルール名")
    current_count: int = Field(description="現在のリクエスト数")
    max_allowed: int = Field(description="許可される最大リクエスト数")
    window_seconds: int = Field(description="制限の時間枠（秒）")
    ip_address: Optional[str] = Field(default=None, description="クライアントIPアドレス")
    user_agent: Optional[str] = Field(default=None, description="ユーザーエージェント")
    endpoint: Optional[str] = Field(default=None, description="アクセスしたエンドポイント")
    user_id: Optional[str] = Field(default=None, description="ユーザーID（認証済みの場合）")
    
    class Config:
        """Pydantic設定"""
        use_enum_values = True

class RateLimitStatus(BaseModel):
    """レート制限の現在の状況"""
    
    identifier: str = Field(description="制限対象の識別子")
    request_type: RateLimitType = Field(description="制限タイプ")
    current_count: int = Field(description="現在のリクエスト数")
    max_allowed: int = Field(description="許可される最大リクエスト数")
    remaining_requests: int = Field(description="残りのリクエスト数")
    window_seconds: int = Field(description="制限の時間枠（秒）")
    reset_time: datetime = Field(description="制限がリセットされる時刻")
    is_blocked: bool = Field(description="現在ブロックされているか")
    
    class Config:
        """Pydantic設定"""
        use_enum_values = True

class RateLimitStats(BaseModel):
    """レート制限の統計情報"""
    
    total_requests: int = Field(description="総リクエスト数")
    blocked_requests: int = Field(description="ブロックされたリクエスト数")
    violations_count: int = Field(description="違反回数")
    active_identifiers: int = Field(description="アクティブな識別子数")
    last_violation: Optional[datetime] = Field(default=None, description="最後の違反時刻")
    
    class Config:
        """Pydantic設定"""
        use_enum_values = True
