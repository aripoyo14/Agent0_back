from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR, DECIMAL
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base
import uuid


# 日本標準時（JST）
JST = timezone(timedelta(hours=9))


class ExpertsPolicyTag(Base):
    """
    エキスパートと政策タグの類似度を保持するテーブル。
    - 1レコードは1回の要約（summary_id）に対するエキスパート×タグのコサイン類似度
    """

    __tablename__ = "experts_policy_tags"

    # テーブル仕様に合わせてUUID文字列を主キーにする
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # エキスパートID（UUID / 文字列36桁を想定）
    expert_id = Column(CHAR(36), nullable=False, index=True)

    # 政策タグID（policy_tags.id）
    policy_tag_id = Column(Integer, ForeignKey("policy_tags.id", ondelete="CASCADE"), nullable=False, index=True)

    # 類似度（DECIMAL(3,2)）。-1.00〜1.00 の範囲を想定
    relation_score = Column(DECIMAL(3, 2), nullable=False)

    # 作成・更新日時
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))

    __table_args__ = (
        # 検索最適化用の複合インデックス
        Index("ix_experts_policy_tags__expert_tag", "expert_id", "policy_tag_id"),
    )


