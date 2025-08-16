"""
セッション関連のデータモデル
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SessionData(BaseModel):
    """セッションデータ"""
    session_id: str = Field(description="セッションID")
    user_id: str = Field(description="ユーザーID")
    user_type: str = Field(description="ユーザータイプ")
    permissions: List[str] = Field(description="権限リスト")
    created_at: datetime = Field(description="作成時刻")
    last_activity: datetime = Field(description="最終アクティビティ")
    ip_address: Optional[str] = Field(default=None, description="IPアドレス")
    user_agent: Optional[str] = Field(default=None, description="ユーザーエージェント")
    is_active: bool = Field(default=True, description="アクティブ状態")

class SessionCreate(BaseModel):
    """セッション作成リクエスト"""
    user_id: str = Field(description="ユーザーID")
    user_type: str = Field(description="ユーザータイプ")
    permissions: List[str] = Field(description="権限リスト")
    ip_address: Optional[str] = Field(default=None, description="IPアドレス")
    user_agent: Optional[str] = Field(default=None, description="ユーザーエージェント")

class TokenResponse(BaseModel):
    """トークンレスポンス"""
    access_token: str = Field(description="アクセストークン")
    refresh_token: str = Field(description="リフレッシュトークン")
    session_id: str = Field(description="セッションID")
    expires_in: int = Field(description="有効期限（秒）")
    token_type: str = Field(default="Bearer", description="トークンタイプ")