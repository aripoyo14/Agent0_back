<<<<<<< HEAD
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Date, Enum, Numeric
from sqlalchemy.dialects.mysql import CHAR, DECIMAL
from sqlalchemy.sql import func
from app.db.base_class import Base
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






