"""
MFA（Multi-Factor Authentication）関連のデータスキーマを定義するモジュール
"""

from pydantic import BaseModel, Field
from typing import List

class MFAEnableRequest(BaseModel):
    """MFA有効化リクエスト用スキーマ"""
    user_id: str = Field(..., description="ユーザーID")
    totp_secret: str = Field(..., description="TOTP秘密鍵")
    backup_codes: List[str] = Field(..., description="バックアップコードのリスト")

class MFAVerifyRequest(BaseModel):
    """TOTPコード検証リクエスト用スキーマ"""
    totp_code: str = Field(..., min_length=6, max_length=6, description="6桁のTOTPコード")

class MFABackupCodeRequest(BaseModel):
    """バックアップコード検証リクエスト用スキーマ"""
    backup_code: str = Field(..., min_length=8, max_length=8, description="8桁のバックアップコード")

class MFAStatusResponse(BaseModel):
    """MFA設定状況レスポンス用スキーマ"""
    mfa_enabled: bool = Field(..., description="MFAが有効化されているか")
    has_backup_codes: bool = Field(..., description="バックアップコードが設定されているか")

class MFASetupResponse(BaseModel):
    """MFA設定完了レスポンス用スキーマ"""
    message: str = Field(..., description="設定完了メッセージ")
    user_id: str = Field(..., description="ユーザーID")
    qr_code_url: str = Field(..., description="QRコードのURL（フロントエンド用）")

class MFAVerificationResponse(BaseModel):
    """MFA検証結果レスポンス用スキーマ"""
    valid: bool = Field(..., description="検証が成功したか")
    message: str = Field(..., description="検証結果メッセージ")
