# app/core/security/rbac/__init__.py

"""
RBAC (Role-Based Access Control) モジュール
ゼロトラストセキュリティの認可基盤
"""

from .permissions import Permission, PERMISSION_GROUPS
from .models import UserRole, ExpertRole, RolePermissionMapping
from .service import RBACService
from .decorators import require_user_permissions, require_expert_permissions

__all__ = [
    "Permission",
    "PERMISSION_GROUPS", 
    "UserRole", 
    "ExpertRole",
    "RolePermissionMapping",
    "RBACService", 
    "require_user_permissions", 
    "require_expert_permissions"
]