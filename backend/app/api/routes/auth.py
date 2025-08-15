# app/api/routes/auth.py
"""
 - ユーザーのログイン認証用APIルートを定義するモジュール。
 - 入力されたメールアドレス・パスワードを検証し、
   有効であればJWTトークンを返す。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.security.jwt import create_access_token
from app.core.security.audit import AuditService, AuditEventType
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert

router = APIRouter(prefix="/auth", tags=["Auth"])

# User/ExpertログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
@router.post("/login", response_model=TokenResponse)
def login_user(http_request: Request, request: LoginRequest, db: Session = Depends(get_db)):

    # 監査サービスの初期化
    audit_service = AuditService(db)

    try:
        # まずUserテーブルで検索
        user = db.query(User).filter(User.email == request.email).first()

        # ユーザーが存在して、パスワードが正しい場合
        if user and verify_password(request.password, user.password_hash):

            # ユーザーの権限を取得
            from app.core.security.rbac.service import RBACService
            user_permissions = RBACService.get_user_permissions(user)

            # Userとしてログイン（スコープ付き）
            token = create_access_token({
                "sub": str(user.id),
                "user_type": "user",
                "role": user.role,
                "scope": list(user_permissions),
            })
            
            # 成功時の監査ログ
            audit_service.log_event(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                user_id=str(user.id),
                user_type="user",
                resource="auth",
                action="login",
                success=True,
                request=http_request,
                details={
                    "email": request.email,
                    "role": user.role,
                    "permissions_count": len(user_permissions)
                }
            )
            
            return TokenResponse(access_token=token)
        
        # Userで見つからない場合、Expertテーブルで検索
        expert = db.query(Expert).filter(Expert.email == request.email).first()
        if expert and verify_password(request.password, expert.password_hash):

            # Expertの権限を取得
            expert_permissions = RBACService.get_expert_permissions(expert)

            # Expertとしてログイン（スコープ付き）
            token = create_access_token({
                "sub": str(expert.id),
                "user_type": "expert",
                "role": expert.role,
                "scope": list(expert_permissions),
            })
            
            # 成功時の監査ログ
            audit_service.log_event(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                user_id=str(expert.id),
                user_type="expert",
                resource="auth",
                action="login",
                success=True,
                request=http_request,
                details={
                    "email": request.email,
                    "role": expert.role,
                    "permissions_count": len(expert_permissions)
                }
            )
            
            return TokenResponse(access_token=token)
        
        # 認証失敗時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILURE,
            resource="auth",
            action="login",
            success=False,
            request=http_request,
            details={
                "email": request.email,
                "reason": "invalid_credentials"
            }
        )
    
        # どちらでも認証失敗
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    except Exception as e:
        # 予期しないエラーの監査ログ
        audit_service.log_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILURE,
            resource="auth",
            action="login",
            success=False,
            request=http_request,
            details={
                "email": request.email,
                "reason": "unexpected_error",
                "error": str(e)
            }
        )
        raise

