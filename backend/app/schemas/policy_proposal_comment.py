#  schemas/policy_proposal_comment.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

# 政策案への新規コメント投稿用スキーマ
class PolicyProposalCommentCreate(BaseModel):
    policy_proposal_id: UUID
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str
    parent_comment_id: Optional[UUID] = None

# コメント取得時のレスポンススキーマ
class PolicyProposalCommentResponse(BaseModel):
    id: UUID
    policy_proposal_id: UUID
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str
    parent_comment_id: Optional[UUID]
    posted_at: datetime
    like_count: int
    is_deleted: bool

    model_config = {
        # Pydantic v2 で ORM 変換を許可
        "from_attributes": True
    }