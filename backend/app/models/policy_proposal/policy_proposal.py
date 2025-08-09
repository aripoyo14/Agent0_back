# app/models/policy_proposal/policy_proposal.py
from sqlalchemy import Column, String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta
import uuid

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

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