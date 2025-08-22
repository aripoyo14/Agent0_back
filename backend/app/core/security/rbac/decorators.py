# app/core/security/rbac/decorators.py
"""
RBACデコレーター
エンドポイントで簡潔に権限チェックを行うための依存関数を提供
"""

from typing import List, Union
from fastapi import Depends, HTTPException, status
from app.core.security.rbac.service import RBACService
from app.core.security.rbac.permissions import Permission
from app.models.user import User
from app.models.expert import Expert


def require_user_permissions(*permissions: Permission):
    """
    ユーザーの権限チェック用デコレーター
    複数の権限を指定可能
    """
    def _checker(current_user: User = Depends()):
        # current_userが正しく渡されることを前提とする
        if not current_user or not hasattr(current_user, 'role'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザー情報が正しく取得できませんでした"
            )
        RBACService.enforce_user_permissions(current_user, list(permissions))
        return current_user
    return _checker


def require_expert_permissions(*permissions: Permission):
    """
    有識者の権限チェック用デコレーター
    
    使用例:
    @router.post("/comments")
    def post_comment(current_expert: Expert = Depends(require_expert_permissions(Permission.COMMENT_CREATE))):
        ...
    """
    def _checker(current_expert: Expert = Depends()):
        if not current_expert or not hasattr(current_expert, 'role'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="有識者情報が正しく取得できませんでした"
            )
        RBACService.enforce_expert_permissions(current_expert, list(permissions))
        return current_expert
    return _checker