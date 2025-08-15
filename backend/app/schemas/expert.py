from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal
from datetime import date, datetime
from uuid import UUID


class ExpertCreate(BaseModel):
    last_name: str
    first_name: str
    company_name: str  # 入力値として受け取り、DBではcompany_idに解決
    department: str
    email: EmailStr
    password: str = Field(min_length=8)


class ExpertOut(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    company_id: Optional[UUID] = None
    department: Optional[str] = None
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# Expertログイン用スキーマ
class ExpertLoginRequest(BaseModel):
    email: EmailStr
    password: str


class ExpertLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expert: ExpertOut

# 外部有識者ロール変更用スキーマ（PUT /{expert_id}/role で使う）
class ExpertRoleUpdateRequest(BaseModel):
    role: str  # "contributor", "viewer" のみ（Expertテーブル用）
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ['contributor', 'viewer']:
            raise ValueError('無効なロールです。contributorまたはviewerのみ許可されます')
        return v