# app/core/security/rbac/models.py
"""
RBAC（Role-Based Access Control）のモデル定義

  - このファイルでは、アプリの「ロール」と「権限」の関係を定義します。
  - DBのユーザーテーブル/有識者テーブルに保存しているロールの値と
    このコード内のロール定義（Enum）が一致するようにしています。
     → これによって、DBの値とアプリのロジックでズレが起きないようにするのが目的です。
"""

from enum import Enum
from typing import Set
from .permissions import Permission, PERMISSION_GROUPS, ALL_PERMISSIONS

""" Userテーブルに対応するロール（職員用） """
class UserRole(str, Enum):

    ADMIN = "admin"      # 管理者：全権限を持つ管理者
    STAFF = "staff"      # 一般職員：基本操作のみ

""" Expertテーブルに対応するロール（外部有識者用） """
class ExpertRole(str, Enum):

    CONTRIBUTOR = "contributor"  # 投稿者：コメント投稿可能
    VIEWER = "viewer"            # 閲覧者：読み取りのみ


""" 各ロールに割り当てる権限一覧（既存DBスキーマ準拠） """
class RolePermissionMapping:

    # Userロールに割り当てる権限
    USER_ROLE_PERMISSIONS = {
        # 管理者
        UserRole.ADMIN: set(ALL_PERMISSIONS),  # 安全なコピーを返す
        
        # 一般職員
        UserRole.STAFF: {
            Permission.USER_READ, Permission.USER_READ_SELF, Permission.POLICY_CREATE, Permission.POLICY_READ,
            Permission.POLICY_UPDATE, Permission.EXPERT_READ, Permission.COMMENT_CREATE,
            Permission.COMMENT_READ, Permission.COMMENT_UPDATE, Permission.FILE_UPLOAD,
            Permission.FILE_DOWNLOAD
        }
    }
    
    # Expertロールに割り当てる権限
    EXPERT_ROLE_PERMISSIONS = {

        # 投稿者
        ExpertRole.CONTRIBUTOR: {
            Permission.POLICY_READ, Permission.EXPERT_READ, Permission.COMMENT_CREATE,
            Permission.COMMENT_READ, Permission.COMMENT_UPDATE, Permission.FILE_DOWNLOAD
        },

        # 閲覧者
        ExpertRole.VIEWER: {
            Permission.POLICY_READ, Permission.EXPERT_READ, Permission.COMMENT_READ,
            Permission.FILE_DOWNLOAD
        }
    }
    
    # Userロールの権限を取得するメソッド
    @classmethod
    def get_user_permissions(cls, role: UserRole) -> Set[Permission]:
        return cls.USER_ROLE_PERMISSIONS.get(role, set())
    
    # Expertロールの権限を取得するメソッド
    @classmethod
    def get_expert_permissions(cls, role: ExpertRole) -> Set[Permission]:
        return cls.EXPERT_ROLE_PERMISSIONS.get(role, set())
    
    # Userロールが指定された権限を持っているかチェックするメソッド
    @classmethod
    def has_user_permission(cls, role: UserRole, permission: Permission) -> bool:
        return permission in cls.get_user_permissions(role)
    
    # Expertロールが指定された権限を持っているかチェックするメソッド
    @classmethod
    def has_expert_permission(cls, role: ExpertRole, permission: Permission) -> bool:
        return permission in cls.get_expert_permissions(role)
    
    # 権限グループ名で権限を取得するメソッド
    @classmethod
    def get_permissions_by_group(cls, group_name: str) -> Set[Permission]:
        return set(PERMISSION_GROUPS.get(group_name, []))
    
    # 全権限を取得するメソッド
    @classmethod
    def get_all_permissions(cls) -> Set[Permission]:
        return set(ALL_PERMISSIONS)
    
    # ロール階層を取得するメソッド
    @classmethod
    def get_role_hierarchy(cls) -> dict:
        # ロール階層の辞書（上位ロールが下位ロールを管理可能）
        return {
            UserRole.ADMIN: [UserRole.STAFF],
            UserRole.STAFF: [],
            ExpertRole.CONTRIBUTOR: [],
            ExpertRole.VIEWER: []
        }
    
    # 管理者が対象ロールを管理できるかチェックするメソッド
    @classmethod
    def can_manage_role(cls, manager_role: UserRole, target_role: UserRole) -> bool:
        if manager_role == UserRole.ADMIN:
            return True
        if manager_role == UserRole.STAFF and target_role == UserRole.STAFF:
            return True
        return False