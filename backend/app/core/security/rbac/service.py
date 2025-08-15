"""
RBACサービスクラス
RBACモデル（権限定義 + マッピング）を実際にアプリのロジックで使える形にするための“実行部” 
"""

from typing import List, Set
from fastapi import HTTPException, status
from app.models.user import User
from app.models.expert import Expert
from .models import UserRole, ExpertRole, RolePermissionMapping
from .permissions import Permission

class RBACService:
    """RBACロジックを提供するサービス層"""

    # --- 権限チェック（True/False返す系） ---
    @staticmethod
    def check_user_permission(user: User, permission: Permission) -> bool:
        if not user or not user.role:
            return False
        try:
            return RolePermissionMapping.has_user_permission(UserRole(user.role), permission)
        except ValueError:
            return False

    @staticmethod
    def check_expert_permission(expert: Expert, permission: Permission) -> bool:
        if not expert or not expert.role:
            return False
        try:
            return RolePermissionMapping.has_expert_permission(ExpertRole(expert.role), permission)
        except ValueError:
            return False

    @staticmethod
    def get_user_permissions(user: User) -> Set[Permission]:
        if not user or not user.role:
            return set()
        try:
            return RolePermissionMapping.get_user_permissions(UserRole(user.role))
        except ValueError:
            return set()

    @staticmethod
    def get_expert_permissions(expert: Expert) -> Set[Permission]:
        if not expert or not expert.role:
            return set()
        try:
            return RolePermissionMapping.get_expert_permissions(ExpertRole(expert.role))
        except ValueError:
            return set()

    @staticmethod
    def has_group_permission(user: User, group_name: str) -> bool:
        """権限グループ単位でチェック"""
        group_perms = RolePermissionMapping.get_permissions_by_group(group_name)
        return any(p in RBACService.get_user_permissions(user) for p in group_perms)

    # --- 権限なしなら即403返す系 ---
    @staticmethod
    def enforce_user_permission(user: User, permission: Permission):
        if not RBACService.check_user_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    @staticmethod
    def enforce_user_permissions(user: User, permissions: List[Permission]):
        user_permissions = RBACService.get_user_permissions(user)
        if not all(p in user_permissions for p in permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="必要な権限が不足しています")

    @staticmethod
    def enforce_group_permission(user: User, group_name: str):
        if not RBACService.has_group_permission(user, group_name):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    # --- ユーザー管理権限の判定 ---
    @staticmethod
    def can_manage_user(manager: User, target_user: User) -> bool:
        if not manager or not target_user:
            return False
        try:
            return RolePermissionMapping.can_manage_role(UserRole(manager.role), UserRole(target_user.role))
        except ValueError:
            return False