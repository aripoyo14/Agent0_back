from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base
import uuid

# 日本標準時間取得
JST = timezone(timedelta(hours=9))  

class User(Base):
    """
    - 経産省職員ユーザー情報を格納するテーブル。
    - UUIDベースのIDを主キーとして使用し、メール・氏名など基本属性を保持。
    - ロールベース（admin / staff）でアクセス制御を行う。
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

    # ユーザーロール：admin=管理者, staff=一般職員（ENUMで明示）
    role = Column(Enum('admin', 'staff', name='user_roles'), nullable=False, default='staff')

    # 最終ログイン日時 （認証成功時に更新）
    last_login_at = Column(DateTime)

    # レコード作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # レコード更新日時（更新時に自動更新 / JST）
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))