"""
監査ログのデータベースモデル
セキュリティイベントの記録と追跡
"""
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON
from app.db.base_class import Base 
import uuid
from app.services.invitation_code import InvitationCodeService
from datetime import datetime, timezone, timedelta
from typing import Optional

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
    
    # ユーザー登録
    USER_REGISTER_SUCCESS = "user:register:success"
    USER_REGISTER_FAILURE = "user:register:failure"
    
    # エキスパート登録
    EXPERT_REGISTER_SUCCESS = "expert:register:success"
    EXPERT_REGISTER_FAILURE = "expert:register:failure"
    
    # MFA設定完了
    MFA_SETUP_COMPLETE = "mfa:setup:complete"

    INVITATION_CODE_GENERATED = "invitation_code_generated"
    INVITATION_CODE_USED = "invitation_code_used"
    INVITATION_CODE_DEACTIVATED = "invitation_code_deactivated"

    # 検索・分析系API - 機密情報へのアクセス追跡
    SEARCH_NETWORK_MAP = "search:network_map"
    SEARCH_MINUTES = "search:minutes"
    SEARCH_POLICY_TAGS = "search:policy_tags"
    SEARCH_EXPERTS = "search:experts"
    SEARCH_POLICY_PROPOSALS = "search:policy_proposals"
    SEARCH_COMMENTS = "search:comments"
    SEARCH_USERS = "search:users"
    SEARCH_DEPARTMENTS = "search:departments"
    SEARCH_POSITIONS = "search:positions"
    
    # データ読み取り系API - 情報漏洩の追跡
    READ_EXPERT_PROFILE = "read:expert:profile"
    READ_EXPERT_INSIGHTS = "read:expert:insights"
    READ_USER_PROFILE = "read:user:profile"
    READ_MEETING_DETAILS = "read:meeting:details"
    READ_MEETING_EVALUATION = "read:meeting:evaluation"
    READ_POLICY_PROPOSAL = "read:policy_proposal"
    READ_POLICY_COMMENTS = "read:policy_comments"
    READ_INVITATION_CODES = "read:invitation_codes"
    READ_SECURITY_STATUS = "read:security:status"
    READ_SECURITY_METRICS = "read:security:metrics"
    READ_SECURITY_CONFIG = "read:security:config"
    
    # 権限変更系API - セキュリティ侵害の追跡
    ROLE_ASSIGNMENT = "role:assignment"
    ROLE_REMOVAL = "role:removal"
    PERMISSION_GRANT = "permission:grant"
    PERMISSION_REVOKE = "permission:revoke"
    USER_ACTIVATION = "user:activation"
    USER_DEACTIVATION = "user:deactivation"
    EXPERT_ACTIVATION = "expert:activation"
    EXPERT_DEACTIVATION = "expert:deactivation"
    MFA_ENABLE = "mfa:enable"
    MFA_DISABLE = "mfa:disable"
    INVITATION_CODE_GENERATE = "invitation_code:generate"
    INVITATION_CODE_DEACTIVATE = "invitation_code:deactivate"


class AuditLog(Base):
    """監査ログテーブル"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}  # この行を追加
    
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
