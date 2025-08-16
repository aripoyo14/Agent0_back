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
from app.core.security.session import session_manager, SessionCreate
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert
from app.core.security.rate_limit.dependencies import check_auth_login_rate_limit

router = APIRouter(prefix="/auth", tags=["Auth"])

# User/ExpertログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
@router.post("/login")
def login_user(
    http_request: Request, 
    request: LoginRequest, 
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_auth_login_rate_limit)  # レート制限チェック
):
    
    # デバッグログを追加
    print(" ログイン関数が呼び出されました")
    print(f"🔍 リクエストIP: {http_request.client.host if http_request.client else 'unknown'}")

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

            # セッション管理を使用してログイン
            session_create = SessionCreate(
                user_id=str(user.id),
                user_type="user",
                permissions=list(user_permissions),
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent")
            )
            
            session_response = session_manager.create_session(session_create)
            
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
                    "permissions_count": len(user_permissions),
                    "session_id": session_response.session_id
                }
            )
            
            return {
                "access_token": session_response.access_token,
                "refresh_token": session_response.refresh_token,
                "session_id": session_response.session_id,
                "expires_in": session_response.expires_in,
                "token_type": session_response.token_type,
                "user_type": "user",
                "role": user.role
            }
        
        # Userで見つからない場合、Expertテーブルで検索
        expert = db.query(Expert).filter(Expert.email == request.email).first()
        if expert and verify_password(request.password, expert.password_hash):

            # Expertの権限を取得
            expert_permissions = RBACService.get_expert_permissions(expert)

            # セッション管理を使用してログイン
            session_create = SessionCreate(
                user_id=str(expert.id),
                user_type="expert",
                permissions=list(expert_permissions),
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent")
            )
            
            session_response = session_manager.create_session(session_create)
            
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
                    "permissions_count": len(expert_permissions),
                    "session_id": session_response.session_id
                }
            )
            
            return {
                "access_token": session_response.access_token,
                "refresh_token": session_response.refresh_token,
                "session_id": session_response.session_id,
                "expires_in": session_response.expires_in,
                "token_type": session_response.token_type,
                "user_type": "expert",
                "role": expert.role
            }
        
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
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証処理中にエラーが発生しました。"
        )

# リフレッシュトークンを使用してアクセストークンを更新
@router.post("/refresh")
async def refresh_token(request: Request):
    """リフレッシュトークンを使用してアクセストークンを更新"""

    # デバッグログを追加
    print(f"🔍 リクエストヘッダー: {dict(request.headers)}")
    print(f"🔍 リクエストメソッド: {request.method}")
    
    try:
        body = await request.json() 
        print(f"🔍 リクエストボディ: {body}")
        refresh_token = body.get("refresh_token")
        print(f" 抽出されたrefresh_token: {refresh_token}")
    except Exception as e:
        print(f"🔍 JSON解析エラー: {e}")
        refresh_token = None
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="リフレッシュトークンが必要です"
        )
    
    # セッション管理サービスでトークンを更新
    try:
        session_response = session_manager.refresh_access_token(refresh_token)
        print(f"🔍 session_response: {session_response}")
        
        if session_response is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです"
            )
    
        return {
                "access_token": session_response.access_token,
                "expires_in": session_response.expires_in,
                "token_type": session_response.token_type
            }
        
    except Exception as e:
        print(f"�� セッション更新エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="トークンの更新に失敗しました"
        )

# ログアウト（セッション無効化）
@router.post("/logout")
def logout(
    session_id: str,
    http_request: Request = None
):
    """セッションを無効化してログアウト"""
    
    success = session_manager.invalidate_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なセッションIDです"
        )
    
    return {"message": "ログアウトしました"}

