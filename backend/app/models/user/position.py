from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class Position(Base):
    """
    - 経産省内の役職情報を格納するテーブル。
    - 多対多中間テーブル（users_positions）と連携予定。
    """

    __tablename__ = "positions"

    # 役職ID（主キー / AUTO_INCREMENT）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 役職名（例：課長補佐、室長、係長など）
    name = Column(String(100), unique=True, nullable=False)

    # アクティブフラグ（廃止役職などに対応）
    is_active = Column(Boolean, default=True)

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 更新日時（JST）
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
