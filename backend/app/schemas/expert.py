from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal, List
from datetime import date, datetime
from uuid import UUID


class ExpertCreate(BaseModel):
    last_name: str
    first_name: str
    company_name: str  # 入力値として受け取り、DBではcompany_idに解決
    department: str
    email: EmailStr
    password: str = Field(min_length=8)
    business_card_image_url: Optional[str] = None


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


# ========== Insights / Overview DTOs ==========

class MeetingParticipantDepartmentOut(BaseModel):
    department_name: str | None = None
    department_section: str | None = None


class MeetingParticipantOut(BaseModel):
    user_id: str
    last_name: str
    first_name: str
    department: MeetingParticipantDepartmentOut | None = None


class MeetingOverviewOut(BaseModel):
    meeting_id: str
    meeting_date: date
    title: str
    summary: str | None = None
    minutes_url: str | None = None
    evaluation: int | None = None
    stance: int | None = None
    participants: list[MeetingParticipantOut] = Field(default_factory=list)
    expert_company_name: str | None = None
    expert_department_name: str | None = None
    expert_title: str | None = None


class PolicyProposalCommentOut(BaseModel):
    policy_proposal_id: str
    policy_title: str
    comment_text: str
    posted_at: datetime
    like_count: int
    evaluation: int | None = None
    stance: int | None = None
    expert_company_name: str | None = None
    expert_department_name: str | None = None
    expert_title: str | None = None


class ExpertInsightsOut(BaseModel):
    expert_id: str
    experts_name: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    department: str | None = None
    email: str | None = None
    mobile: str | None = None
    title: str | None = None
    meetings: list[MeetingOverviewOut]
    policy_comments: list[PolicyProposalCommentOut]
    evaluation_average: float | None = None  # 小数第1位
    stance_average: int | None = None       # 四捨五入の整数


# 既存のスキーマに追加
class ExpertRegisterResponse(BaseModel):
    message: str
    user_id: str
    mfa_setup_required: bool
    totp_secret: str
    backup_codes: List[str]
    qr_code_url: str
    next_step: str