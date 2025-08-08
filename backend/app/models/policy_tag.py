from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class PolicyTag(Base):
    """
    - 政策タグ情報を格納するテーブル
    - idとnameをベクトル化してPineconeに保存する
    """

    __tablename__ = "policy_tags"

    # タグID（主キー / AUTO_INCREMENT）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # タグ名
    name = Column(String(50), nullable=False)

    # ベクトル化されたデータ（JSON形式で保存）
    embedding = Column(Text, nullable=True)

    # 作成日時
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 更新日時
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
