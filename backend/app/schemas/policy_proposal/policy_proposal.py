# app/schemas/policy_proposal/policy_proposal.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from uuid import UUID

# 投稿ステータスを定義
PolicyStatus = Literal["draft", "published", "archived"]

# 政策案新規登録用スキーマ
class ProposalCreate(BaseModel):
    title: str = Field(max_length=255)
    body: str
    published_by_user_id: UUID
    status: PolicyStatus = "draft"

# レスポンス用スキーマ（表示用）
class ProposalOut(BaseModel):
    id: UUID
    title: str
    body: str
    published_by_user_id: UUID
    status: PolicyStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }