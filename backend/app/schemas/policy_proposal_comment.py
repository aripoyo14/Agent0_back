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
    evaluation: Optional[int] = Field(None, ge=1, le=5)  # 純粋な評価（1-5：悪い-良い）
    stance: Optional[int] = Field(None, ge=1, le=5)      # スタンス（1-5：否定的-肯定的）

# 既存：単一コメント
class PolicyProposalCommentResponse(BaseModel):
    id: UUID
    policy_proposal_id: UUID
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str
    parent_comment_id: Optional[UUID]
    posted_at: datetime
    # updated_at: Optional[datetime] = None  # 一時的にコメントアウト（DBマイグレーション後有効化）
    like_count: int
    is_deleted: bool
    evaluation: Optional[int] = None  # 純粋な評価（1-5：悪い-良い）
    stance: Optional[int] = None      # スタンス（1-5：否定的-肯定的）

    model_config = {
        # Pydantic v2 で ORM 変換を許可
        "from_attributes": True
    }

# 返信投稿用スキーマ（親コメントIDはパスパラメータで受け取るため本体には含めない）
class PolicyProposalReplyCreate(BaseModel):
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    comment_text: str
    evaluation: Optional[int] = Field(None, ge=1, le=5)  # 純粋な評価（1-5：悪い-良い）
    stance: Optional[int] = Field(None, ge=1, le=5)      # スタンス（1-5：否定的-肯定的）

# AI 返信リクエスト
class AIReplyRequest(BaseModel):
    author_type: Literal["admin", "staff", "contributor", "viewer"]
    author_id: UUID
    persona: Optional[str] = "丁寧で建設的な政策担当者"
    instruction: Optional[str] = None

# 評価投稿用スキーマ
class CommentRatingCreate(BaseModel):
    evaluation: Optional[int] = Field(None, ge=1, le=5)  # 純粋な評価（1-5：悪い-良い）
    stance: Optional[int] = Field(None, ge=1, le=5)      # スタンス（1-5：否定的-肯定的）

# 評価レスポンス用スキーマ
class CommentRatingResponse(BaseModel):
    id: UUID
    evaluation: Optional[int] = None
    stance: Optional[int] = None
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

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