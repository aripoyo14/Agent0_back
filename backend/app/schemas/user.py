from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


# ユーザー登録用スキーマ（POST /register で使う）
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    last_name: str
    first_name: str
    extension: Optional[str] = None
    direct_phone: Optional[str] = None
    department_id: int  
    position_id: int    

# ユーザー表示用（レスポンスなどで使用）
class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    last_name: str
    first_name: str
    extension: Optional[str] = None
    direct_phone: Optional[str] = None
    is_active: bool
    role: Literal['admin', 'staff']
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    mfa_enabled: Optional[bool] = False
    # mfa_totp_secret と mfa_backup_codes はセキュリティ上、レスポンスには含めない

    model_config = {
        # Pydantic v2 で ORM 変換を許可
        "from_attributes": True
    }


# ユーザーログイン用スキーマ（POST /login で使う）
class UserLoginRequest(BaseModel):
    email: str
    password: str

# ユーザーログイン用スキーマ（POST /login で使う）
class UserLoginResponse(BaseModel):
    access_token: str
    user: UserOut


# MFA設定用スキーマ
class MFAEnableRequest(BaseModel):
    totp_secret: str
    backup_codes: list[str]

class MFAVerifyRequest(BaseModel):
    totp_code: str

class MFABackupCodeRequest(BaseModel):
    backup_code: str

# ユーザーロール変更用スキーマ（PUT /{user_id}/role で使う）
class RoleUpdateRequest(BaseModel):
    role: str  # "admin", "staff" のみ
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ['admin', 'staff']:
            raise ValueError('無効なロールです。adminまたはstaffのみ許可されます')
        return v