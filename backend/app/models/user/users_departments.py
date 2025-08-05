from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class UsersDepartments(Base):
    """
    - 経産省職員（users）と部署（departments）の中間テーブル。
    - 多対多関係を表現するために使用。
    """

    __tablename__ = "users_departments"

    # 主キー（AUTO_INCREMENT）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ユーザーID（外部キー）
    user_id = Column(ForeignKey("users.id"), nullable=False)

    # 部署ID（外部キー）
    department_id = Column(ForeignKey("departments.id"), nullable=False)

    # 有効フラグ（過去所属などを残す場合に利用）
    is_active = Column(Boolean, default=True)

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 更新日時（JST）
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
