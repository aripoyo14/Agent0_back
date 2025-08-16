"""
ゼロトラストセキュリティモジュール
"""

# パスワード関連の関数をエクスポート
from .password import hash_password, verify_password

# JWT関連の機能をエクスポート
from .jwt import create_access_token, verify_access_token, decode_access_token

# MFA関連の機能をエクスポート
from .mfa import mfa_router, MFAService, enable_mfa, disable_mfa, update_mfa_backup_codes, get_mfa_status, verify_mfa_totp, verify_mfa_backup_code

# RBAC関連の機能をエクスポート
from .rbac import RBACService, require_user_permissions, require_expert_permissions

# 監査ログ関連の機能をエクスポート
from .audit import AuditService, AuditEventType, audit_log, audit_log_sync

# レート制限関連の機能をエクスポート
from .rate_limit import (
    rate_limit, rate_limit_ip, rate_limit_endpoint, rate_limit_user,
    rate_limit_auth_login, rate_limit_user_register, rate_limit_file_upload,
    rate_limit_comment_post, rate_limit_read_api
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_access_token",
    "decode_access_token",
    "mfa_router",
    "MFAService",
    "RBACService",
    "require_user_permissions",
    "require_expert_permissions",
    "AuditService",
    "AuditEventType",
    "audit_log",
    "audit_log_sync",
    "rate_limit",
    "rate_limit_ip",
    "rate_limit_endpoint",
    "rate_limit_user",
    "rate_limit_auth_login",
    "rate_limit_user_register",
    "rate_limit_file_upload",
    "rate_limit_comment_post",
    "rate_limit_read_api"
]