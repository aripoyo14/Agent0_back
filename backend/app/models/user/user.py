from sqlalchemy import Column, String, Boolean, DateTime, Enum, JSON
from typing import Optional, List
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
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

    # MFAを有効化済みか
    mfa_enabled: bool = Column(Boolean, default=False, nullable=False)

    # MFAを必須化するか
    mfa_required: bool = Column(Boolean, default=False, nullable=False)
    
    # TOTPの秘密鍵（暗号化）
    mfa_totp_secret = Column(String(255), nullable=True)

    # バックアップコード群（暗号化）
    mfa_backup_codes: Optional[List[str]] = Column(JSON, nullable=True)

    # アカウント状態
    account_active: bool = Column(Boolean, default=True, nullable=False)

    # リレーション
    organized_meetings = relationship("Meeting", back_populates="organizer")
    meeting_participations = relationship("MeetingUser", back_populates="user")

    # 暗号化機能の追加
    def _get_encryption_service(self):
        """暗号化サービスを遅延インポートで取得"""
        from app.core.security.encryption import encryption_service
        return encryption_service

    # 暗号化されたデータの復号化メソッド
    def get_decrypted_email(self) -> str:
        """暗号化されたメールアドレスを復号化して返す"""
        if self.email:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.email)
            except Exception:
                # 復号化に失敗した場合（古いデータなど）はそのまま返す
                return self.email
        return ""

    def get_decrypted_extension(self) -> str:
        """暗号化された内線番号を復号化して返す"""
        if self.extension:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.extension)
            except Exception:
                return self.extension
        return ""

    def get_decrypted_direct_phone(self) -> str:
        """暗号化された直通番号を復号化して返す"""
        if self.direct_phone:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.direct_phone)
            except Exception:
                return self.direct_phone
        return ""

    def get_decrypted_mfa_totp_secret(self) -> str:
        """暗号化されたMFA秘密鍵を復号化して返す"""
        if self.mfa_totp_secret:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.mfa_totp_secret)
            except Exception:
                return self.mfa_totp_secret
        return ""

    def get_decrypted_mfa_backup_codes(self) -> List[str]:
        """暗号化されたMFAバックアップコードを復号化して返す"""
        if self.mfa_backup_codes:
            try:
                encryption_service = self._get_encryption_service()
                # JSONデータの場合は個別に復号化
                decrypted_codes = []
                for code in self.mfa_backup_codes:
                    if isinstance(code, str):
                        decrypted_codes.append(encryption_service.decrypt_data(code))
                    else:
                        decrypted_codes.append(str(code))
                return decrypted_codes
            except Exception:
                return self.mfa_backup_codes
        return []

    # 暗号化メソッド（新規データ保存時用）
    def encrypt_sensitive_data(self):
        """機密データを暗号化する"""
        encryption_service = self._get_encryption_service()
        
        if self.email:
            self.email = encryption_service.encrypt_data(self.email)
        if self.extension:
            self.extension = encryption_service.encrypt_data(self.extension)
        if self.direct_phone:
            self.direct_phone = encryption_service.encrypt_data(self.direct_phone)
        if self.mfa_totp_secret:
            self.mfa_totp_secret = encryption_service.encrypt_data(self.mfa_totp_secret)
        if self.mfa_backup_codes:
            # バックアップコードの配列を個別に暗号化
            encrypted_codes = []
            for code in self.mfa_backup_codes:
                if isinstance(code, str):
                    encrypted_codes.append(encryption_service.encrypt_data(code))
                else:
                    encrypted_codes.append(str(code))
            self.mfa_backup_codes = encrypted_codes