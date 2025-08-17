# app/models/policy_proposal/policy_proposal.py
from sqlalchemy import Column, String, Text, Enum, DateTime, ForeignKey, Table, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta
import uuid

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

# 中間テーブルの定義
policy_proposals_policy_tags = Table(
    'policy_proposals_policy_tags',
    Base.metadata,
    Column('policy_proposal_id', CHAR(36), ForeignKey('policy_proposals.id', ondelete='CASCADE'), primary_key=True),
    Column('policy_tag_id', Integer, ForeignKey('policy_tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=lambda: datetime.now(JST))
)

class PolicyProposal(Base):
    """
    - 政策案を格納するテーブルのモデル定義。
    - 投稿者（users）との外部キー制約あり。
    """

    __tablename__ = "policy_proposals"

    # 主キー：UUID
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # タイトル（255文字制限）
    title = Column(String(255), nullable=False)

    # 本文（TEXT型）
    body = Column(Text, nullable=False)

    # 投稿者（user.idへの外部キー）
    published_by_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)

    # 投稿ステータス（draft / published / archived）
    status = Column(
        Enum("draft", "published", "archived"),
        nullable=False,
        default="draft"
    )

    # 公開日時（NULL可）
    published_at = Column(DateTime, nullable=True)

    # 作成・更新日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))

    # 添付ファイル（1対多）
    attachments = relationship(
        "PolicyProposalAttachment",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )

    # 政策タグ（多対多）
    policy_tags = relationship(
        "PolicyTag",
        secondary=policy_proposals_policy_tags,
        back_populates="policy_proposals"
    )