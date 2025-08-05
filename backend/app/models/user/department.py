from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class Department(Base):
    """
    - 経産省内の部局・部署情報を格納するテーブル。
    - 多対多中間テーブル（users_departments）と連携予定。
    """

    __tablename__ = "departments"

    # 部署ID（主キー / AUTO_INCREMENT）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 部局名（例：商務情報政策局）
    name = Column(String(50), nullable=False)

    # 部署・課名（例：情報技術利用促進課）
    section = Column(String(50), nullable=True)

    # アクティブフラグ（廃止部署などに対応）
    is_active = Column(Boolean, default=True)

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 更新日時（JST）
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
