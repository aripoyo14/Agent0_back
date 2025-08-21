from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, Boolean, DateTime, Date, Enum, JSON, ForeignKey
from typing import Optional, List
from sqlalchemy.dialects.mysql import CHAR, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
# 循環インポートを避けるため、遅延インポートに変更
# from app.core.security.encryption import encryption_service
import uuid

JST = timezone(timedelta(hours=9))

# えんちゃんバージョン(認証トークン付きログイン機能追加)
class Expert(Base):
    __tablename__ = "experts"

    id = Column(CHAR(36), primary_key=True)
    sansan_person_id = Column(String(100))
    last_name = Column(String(50), index=True, nullable=False)
    first_name = Column(String(50), index=True, nullable=False)
    company_id = Column(CHAR(36), index=True)
    department = Column(String(100))
    title = Column(String(100))
    email = Column(String(255))
    password_hash = Column(String(255))
    mobile = Column(String(20))
    contact_frequency = Column(String(11))
    last_contact_date = Column(Date)
    overall_relevance = Column(DECIMAL(3, 2))
    policy_relevance = Column(DECIMAL(3, 2))
    expertise_score = Column(DECIMAL(3, 2))
    memo = Column(String)
    sansan_sync_status = Column(Enum('pending', 'synced', 'error', name='sansan_sync_status'))
    sync_error_message = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
    role = Column(Enum('contributor', 'viewer', name='expert_role'), default='viewer')

    # 招待関連フィールド（新規追加）
    invited_by_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    invited_by_expert_id = Column(CHAR(36), ForeignKey("experts.id"), nullable=True)
    invitation_code = Column(String(100), nullable=True)
    invited_at = Column(DateTime, nullable=True)

    # MFA関連フィールド（新規追加）
    mfa_enabled: bool = Column(Boolean, default=False, nullable=False)
    mfa_required: bool = Column(Boolean, default=False, nullable=False) 
    mfa_totp_secret: Optional[str] = Column(String, nullable=True)
    mfa_backup_codes: Optional[List[str]] = Column(JSON, nullable=True)
    
    # アカウント状態フィールド
    account_active: bool = Column(Boolean, default=True, nullable=False)
    
    # 登録状態フィールド（新規追加）
    registration_status: str = Column(
        Enum('pending_mfa', 'active', 'suspended', name='expert_registration_status'),
        default='pending_mfa',
        nullable=False
    )

    # 名刺画像関連のカラムを追加
    business_card_image_url = Column(String(500), nullable=True, comment="名刺画像のURL")

    # リレーション
    meeting_participations = relationship("MeetingExpert", back_populates="expert")
    invited_by_user = relationship("User", foreign_keys=[invited_by_user_id])
    invited_by_expert = relationship("Expert", foreign_keys=[invited_by_expert_id], remote_side=[id])

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

    def get_decrypted_mobile(self) -> str:
        """暗号化された携帯電話番号を復号化して返す"""
        if self.mobile:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.mobile)
            except Exception:
                return self.mobile
        return ""

    def get_decrypted_memo(self) -> str:
        """暗号化されたメモを復号化して返す"""
        if self.memo:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.memo)
            except Exception:
                return self.memo
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

    def get_decrypted_sansan_person_id(self) -> str:
        """暗号化されたSanSan個人IDを復号化して返す"""
        if self.sansan_person_id:
            try:
                encryption_service = self._get_encryption_service()
                return encryption_service.decrypt_data(self.sansan_person_id)
            except Exception:
                return self.sansan_person_id
        return ""

    # 暗号化メソッド（新規データ保存時用）
    def encrypt_sensitive_data(self):
        """機密データを暗号化する"""
        encryption_service = self._get_encryption_service()
        
        if self.email:
            self.email = encryption_service.encrypt_data(self.email)
        if self.mobile:
            self.mobile = encryption_service.encrypt_data(self.mobile)
        if self.memo:
            self.memo = encryption_service.encrypt_data(self.memo)
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
        if self.sansan_person_id:
            self.sansan_person_id = encryption_service.encrypt_data(self.sansan_person_id)

# 人脈マップ作成時に変わっていた（いったんコメントアウト）
# class Expert(Base):
#     """
#     外部有識者情報（SanSan連携）テーブル。
#     既存のMySQLスキーマに準拠。
#     """

#     __tablename__ = "experts"

#     # 主キー（UUID文字列 / 固定長）
#     id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

#     # SanSan人物ID（ユニーク、NULL許可：未連携時はNULL）
#     sansan_person_id = Column(String(100), unique=True, nullable=True)

#     # 氏名
#     last_name = Column(String(50), nullable=False)
#     first_name = Column(String(50), nullable=False)

#     # 会社ID（UUID / companies.idへの参照を想定）
#     company_id = Column(CHAR(36), nullable=True)

#     # プロフィール（SanSan由来）
#     department = Column(String(100))
#     title = Column(String(100))
#     email = Column(String(255))
#     # 認証用パスワードハッシュ
#     password_hash = Column(String(255))
#     mobile = Column(String(20))

#     # 連絡状況
#     contact_frequency = Column(Integer, default=0)
#     last_contact_date = Column(Date)

#     # スコア（0-1 / DECIMAL(3,2)）
#     overall_relevance = Column(Numeric(3, 2))
#     policy_relevance = Column(Numeric(3, 2))
#     expertise_score = Column(Numeric(3, 2))

#     # メモ
#     memo = Column(Text)

#     # 同期ステータスとエラーメッセージ
#     sansan_sync_status = Column(String(20), nullable=False, server_default="pending")
#     sync_error_message = Column(Text)

#     # コメント投稿権限の区分
#     role = Column(Enum("contributor", "viewer", name="expert_roles"), nullable=False, server_default="contributor")

#     # タイムスタンプ（DB側のDEFAULT / ON UPDATE）
#     created_at = Column(DateTime, server_default=func.current_timestamp())
#     updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())






