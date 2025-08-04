from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime, timezone
from app.db.base_class import Base
import uuid

class User(Base):
    """
    - 経産省職員ユーザー情報を格納するテーブル。
    - UUIDベースのIDを主キーとして使用し、メール・氏名など基本属性を保持。
    """

    __tablename__ = "users"

    # ユーザーID （UUID / 主キー / 固定長）
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # ログインID （メールアドレス） ※一意制約
    email = Column(String(255), unique=True, nullable=False)

    # ハッシュ化されたパスワード
    password_hash = Column(String(255), nullable=False)

    # 姓
    last_name = Column(String(50), nullable=False)

    # 名
    first_name = Column(String(50), nullable=False)

    # 内線番号 （任意）
    extension = Column(String(20))

    # 直通番号 （任意）
    direct_phone = Column(String(20))

    # 利用可能フラグ （論理削除などに利用）
    is_active = Column(Boolean, default=True)

    # 管理者フラグ （Trueで管理権限あり）
    is_admin = Column(Boolean, default=False)

    # 最終ログイン日時 （認証成功時に更新）
    last_login_at = Column(DateTime)

    # レコード作成日時 （UTC）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # レコード更新日時 （更新時に自動更新 / UTC）
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))