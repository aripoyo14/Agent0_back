"""
監査ログのデータベースモデル
セキュリティイベントの記録と追跡
"""
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON
from app.db.database import Base 
import uuid

# 日本標準時（JST）のタイムゾーンを定義
JST = timezone(timedelta(hours=9))

class AuditEventType(str, Enum):
    """監査イベントのタイプ"""
    # 認証・認可
    AUTH_LOGIN_SUCCESS = "auth:login:success"
    AUTH_LOGIN_FAILURE = "auth:login:failure"
    AUTH_LOGOUT = "auth:logout"
    AUTH_PERMISSION_DENIED = "auth:permission:denied"
    AUTH_ROLE_CHANGE = "auth:role:change"
    
    # データアクセス
    DATA_READ = "data:read"
    DATA_CREATE = "data:create"
    DATA_UPDATE = "data:update"
    DATA_DELETE = "data:delete"
    
    # ファイル操作
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FILE_DELETE = "file:delete"
    
    # システム操作
    SYSTEM_CONFIG_CHANGE = "system:config:change"
    SYSTEM_ADMIN_ACTION = "system:admin:action"
    
    # セキュリティ
    SECURITY_ALERT = "security:alert"
    MFA_ENABLED = "mfa:enabled"
    MFA_DISABLED = "mfa:disabled"


class AuditLog(Base):
    """監査ログテーブル"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.now(JST), nullable=False)
    user_id = Column(String, nullable=True)  # 匿名アクセスの場合もある
    user_type = Column(String, nullable=True)  # "user" or "expert"
    event_type = Column(String, nullable=False)
    resource = Column(String, nullable=True)  # 操作対象のリソース
    action = Column(String, nullable=True)    # 実行されたアクション
    success = Column(Boolean, default=True)   # 成功/失敗
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)     # 追加の詳細情報
    session_id = Column(String, nullable=True)  # セッション識別子
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"
