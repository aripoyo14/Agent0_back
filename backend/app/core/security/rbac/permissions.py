# app/core/security/rbac/permissions.py
"""
操作権限の定義
"""

from enum import Enum

""" 操作権限一覧 """
class Permission(str, Enum):

    # --- ユーザー（経産省職員）管理 ---
    USER_CREATE = "user:create"        # ユーザー作成
    USER_READ = "user:read"            # ユーザー情報閲覧
    USER_UPDATE = "user:update"        # ユーザー情報更新
    USER_DELETE = "user:delete"        # ユーザー削除
    USER_ROLE_CHANGE = "user:role_change"    # ユーザーのロール変更
    USER_READ_SELF = "user:read_self"  # 自分の情報読み取り
    
    # --- 政策案管理 ---
    POLICY_CREATE = "policy:create"    # 政策案作成
    POLICY_READ = "policy:read"        # 政策案閲覧
    POLICY_UPDATE = "policy:update"    # 政策案更新
    POLICY_DELETE = "policy:delete"    # 政策案削除
    
    # --- 外部有識者管理 ---
    EXPERT_CREATE = "expert:create"    # 外部有識者作成
    EXPERT_READ = "expert:read"        # 外部有識者閲覧
    EXPERT_UPDATE = "expert:update"    # 外部有識者更新
    EXPERT_DELETE = "expert:delete"    # 外部有識者削除
    
    # --- システム管理 ---
    SYSTEM_CONFIG = "system:config"    # システム設定変更
    SYSTEM_ADMIN = "system:admin"      # システム管理者権限（全アクセス）
    
    # --- コメント管理 ---
    COMMENT_CREATE = "comment:create"    # コメント作成
    COMMENT_READ = "comment:read"        # コメント閲覧
    COMMENT_UPDATE = "comment:update"    # コメント更新
    COMMENT_DELETE = "comment:delete"    # コメント削除
    
    # --- ファイル管理 ---
    FILE_UPLOAD = "file:upload"        # ファイルアップロード
    FILE_DOWNLOAD = "file:download"    # ファイルダウンロード
    FILE_DELETE = "file:delete"        # ファイル削除
    
    # --- 検索・ネットワークマップ管理（経産省職員のみ） ---
    SEARCH_NETWORK_READ = "search_network:read"    # ネットワークマップ検索・閲覧（経産省職員のみ）
    SEARCH_NETWORK_EXPORT = "search_network:export"    # ネットワークマップデータエクスポート（経産省職員のみ）

""" 権限グループ（関連する権限をまとめる） """
PERMISSION_GROUPS = {

    # ユーザー（経産省職員）管理関連
    "user_management": [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
        Permission.USER_DELETE, Permission.USER_ROLE_CHANGE
    ],

    # 政策案管理関連
    "policy_management": [
        Permission.POLICY_CREATE, Permission.POLICY_READ, Permission.POLICY_UPDATE,
        Permission.POLICY_DELETE
    ],

    # 外部有識者管理関連
    "expert_management": [
        Permission.EXPERT_CREATE, Permission.EXPERT_READ, Permission.EXPERT_UPDATE,
        Permission.EXPERT_DELETE
    ],

    # システム管理関連
    "system_management": [
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_ADMIN
    ],
    
    # コメント管理関連
    "comment_management": [
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.COMMENT_DELETE
    ],

    # ファイル管理関連
    "file_management": [
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD, Permission.FILE_DELETE
    ],
    
    # 検索・ネットワークマップ関連（経産省職員のみ）
    "search_network_management": [
        Permission.SEARCH_NETWORK_READ, Permission.SEARCH_NETWORK_EXPORT
    ]
}

""" 全権限セット（ADMIN用：全ての操作が可能） """
ALL_PERMISSIONS = set(Permission)
