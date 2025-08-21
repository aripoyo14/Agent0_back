from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class InvitationCodeType(str, Enum):
    EXPERT = "expert"
    USER = "user"

class InvitationCodeCreate(BaseModel):
    """招待QRコード作成用スキーマ"""
    code_type: InvitationCodeType = InvitationCodeType.EXPERT
    max_uses: int = Field(default=1, ge=1, le=100)
    expires_in_hours: int = Field(default=24, ge=1, le=720)  # 1時間〜30日
    description: Optional[str] = Field(max_length=255)

class InvitationCodeResponse(BaseModel):
    """招待QRコード発行結果用スキーマ"""
    code: str
    invitation_link: str  # 招待リンク
    qr_code_data: str     # QRコードのデータ（Base64エンコードされた画像）
    code_type: InvitationCodeType
    max_uses: int
    expires_at: datetime
    description: Optional[str]
    message: str

class InvitationCodeValidation(BaseModel):
    """招待コード検証用スキーマ"""
    code: str = Field(min_length=1, max_length=20)

class InvitationCodeValidationResponse(BaseModel):
    """招待コード検証結果用スキーマ"""
    is_valid: bool
    code_type: Optional[InvitationCodeType] = None
    message: str
    issuer_info: Optional[dict] = None
