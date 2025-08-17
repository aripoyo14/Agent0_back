# app/schemas/policy_proposal/policy_proposal.py
from pydantic import BaseModel, Field
from typing import Literal, List
from datetime import datetime
from uuid import UUID

# 投稿ステータスを定義
PolicyStatus = Literal["draft", "published", "archived"]

# 政策タグ用スキーマ
class PolicyTagOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    keywords: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# 政策案新規登録用スキーマ
class ProposalCreate(BaseModel):
    title: str = Field(max_length=255)
    body: str
    published_by_user_id: UUID
    status: PolicyStatus = "draft"

# 添付作成用スキーマ
class AttachmentCreate(BaseModel):
    file_name: str
    file_type: str | None = None
    file_size: int | None = None


# 添付返却用スキーマ
class AttachmentOut(BaseModel):
    id: UUID
    policy_proposal_id: UUID
    file_name: str
    file_url: str
    file_type: str | None
    file_size: int | None
    uploaded_by_user_id: UUID | None
    uploaded_at: datetime

    model_config = {
        "from_attributes": True
    }


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
    # 添付一覧（省略可能）
    attachments: list[AttachmentOut] | None = None
    # 政策タグ一覧（省略可能）
    policy_tags: list[PolicyTagOut] | None = None

    model_config = {
        "from_attributes": True
    }

    @classmethod
    def from_proposal_with_relations(cls, proposal):
        """
        政策提案オブジェクトからレスポンス用オブジェクトを作成
        政策タグ情報も含めて適切にマッピングする
        """
        # 基本情報
        data = {
            "id": proposal.id,
            "title": proposal.title,
            "body": proposal.body,
            "published_by_user_id": proposal.published_by_user_id,
            "status": proposal.status,
            "published_at": proposal.published_at,
            "created_at": proposal.created_at,
            "updated_at": proposal.updated_at,
        }
        
        # 添付ファイル情報
        if hasattr(proposal, 'attachments') and proposal.attachments:
            data["attachments"] = [AttachmentOut.from_orm(att) for att in proposal.attachments]
        else:
            data["attachments"] = None
            
        # 政策タグ情報
        if hasattr(proposal, 'tags') and proposal.tags:
            data["policy_tags"] = [PolicyTagOut.from_orm(tag.tag) for tag in proposal.tags if tag.tag]
        else:
            data["policy_tags"] = None
            
        return cls(**data)