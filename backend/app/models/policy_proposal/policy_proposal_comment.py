# app/models/policy_proposal/policy_proposal_comment.py
from sqlalchemy import Column, ForeignKey, Text, DateTime, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base
import uuid

# 日本標準時間取得
JST = timezone(timedelta(hours=9))  

class PolicyProposalComment(Base):
    """
    - 政策案に対するコメントを格納するテーブル。
    - 投稿者は経産省職員（users）または外部有識者（experts）を区別。
    - 返信構造・いいね数・削除フラグなども含む。
    """

    __tablename__ = "policy_proposal_comments"

    # コメントID（UUID / 主キー）
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 紐づく政策案ID（外部キー）
    policy_proposal_id = Column(CHAR(36), ForeignKey("policy_proposals.id"), nullable=False)

    # 投稿者の種別：user or expert
    author_type = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "author_type IN ('admin', 'staff', 'contributor', 'viewer')",
            name="check_author_type"
        ),
    )

    # 投稿者ID（users.id または experts.id）
    author_id = Column(CHAR(36), nullable=False)

    # コメント本文
    comment_text = Column(Text, nullable=False)

    # 親コメントID（返信先）※NULL可
    parent_comment_id = Column(CHAR(36), ForeignKey("policy_proposal_comments.id"), nullable=True)

    # 投稿日時（JST）
    posted_at = Column(DateTime, default=lambda: datetime.now(JST))

    # いいね数（初期値0）
    like_count = Column(Integer, default=0)

    # ソフトデリート（論理削除）
    is_deleted = Column(Boolean, default=False)