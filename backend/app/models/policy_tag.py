# app/models/policy_tag.py
from sqlalchemy import Column, String, Text, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class PolicyTag(Base):
    """
    - 政策カテゴリー（専門性タグ）を格納するモデル。
    - 顧客の専門分野や政策案とのマッチングに利用可能。
    """

    __tablename__ = "policy_tags"

    # 主キー：AUTO_INCREMENTの整数ID
    id = Column(Integer, primary_key=True, autoincrement=True)

    # タグ名（50文字以内）ユニーク制約
    name = Column(String(50), nullable=False, unique=True)

    # 説明・キーワード（任意）
    description = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)

    # ベクトル値（1536次元の埋め込みをJSON文字列化して保存）
    # ※ MySQLにpgvector相当の拡張がなければTEXTでOK
    embedding = Column(Text, nullable=True, comment="JSON文字列形式の埋め込みベクトル")

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 更新日時（JST）
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))

    # 政策提案（多対多）
    policy_proposals = relationship(
        "PolicyProposal",
        secondary="policy_proposals_policy_tags",
        back_populates="policy_tags"
    )