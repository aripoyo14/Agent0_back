# app/models/policy_proposal/policy_proposals_policy_tags.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class PolicyProposalsPolicyTags(Base):
    """
    - 政策案と政策関連タグの中間テーブル（複合PK）。
    - 1つの政策案に複数タグ、1つのタグが複数政策案に付与される多対多を実現。
    """

    __tablename__ = "policy_proposals_policy_tags"

    # 政策案ID（外部キー → policy_proposals.id）
    policy_proposal_id = Column(
        CHAR(36), 
        ForeignKey("policy_proposals.id", ondelete="CASCADE"), 
        nullable=False
    )

    # タグID（外部キー → policy_tags.id）
    policy_tag_id = Column(
        Integer, 
        ForeignKey("policy_tags.id", ondelete="CASCADE"), 
        nullable=False
    )

    # 登録日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # リレーション（必要なら）
    proposal = relationship("PolicyProposal", back_populates="tags")
    tag = relationship("PolicyTag")

    # 複合PK & 補助インデックスを設定
    __table_args__ = (
        # 複合PK:「policy_proposal_id」と「policy_tag_id」のセットで主キー
        PrimaryKeyConstraint("policy_proposal_id", "policy_tag_id", name="pk_proposal_tag"),
        
        # 補助インデックス
        Index("ix_policy_proposal_tags__policy_tag_id", "policy_tag_id"),
    )