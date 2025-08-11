#  schemas/policy_proposal_comment.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime

# 政策案への新規コメント投稿用スキーマ
class PolicyProposalCommentCreate(BaseModel):
    policy_proposal_id: UUID
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str
    parent_comment_id: Optional[UUID] = None

# 既存：単一コメント
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

# 返信投稿用スキーマ（親コメントIDはパスパラメータで受け取るため本体には含めない）
class PolicyProposalReplyCreate(BaseModel):
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str

# AI 返信リクエスト
class AIReplyRequest(BaseModel):
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    persona: Optional[str] = "丁寧で建設的な政策担当者"
    instruction: Optional[str] = None

# 政策ごとに束ねる器（拡張メタ付き）
class PolicyWithComments(BaseModel):
    policy_proposal_id: UUID
    title: Optional[str] = None
    status: Optional[str] = None
    published_at: Optional[datetime] = None

    latest_commented_at: Optional[datetime] = None
    total_comments: int

    page: int = 1
    page_size: int = 20
    has_next: bool = False

    comments: List[PolicyProposalCommentResponse]

    model_config = {
        "from_attributes": True
    }

# コメント一覧取得時のレスポンススキーマ
class PolicyProposalCommentListResponse(BaseModel):
    policy_proposal_id: UUID
    title: Optional[str] = None
    status: Optional[str] = None
    published_at: Optional[datetime] = None

    latest_commented_at: Optional[datetime] = None
    total_comments: int