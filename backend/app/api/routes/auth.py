# app/api/routes/auth.py
"""
 - ユーザーのログイン認証用APIルートを定義するモジュール。
 - 入力されたメールアドレス・パスワードを検証し、
   有効であればJWTトークンを返す。
"""

import inspect
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.security.jwt import create_access_token
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.audit.decorators import continuous_verification_audit
from app.core.security.session import session_manager, SessionCreate
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert
from app.core.security.rbac.service import RBACService
from app.core.security.rate_limit.dependencies import check_auth_login_rate_limit

# 既存のインポートに追加
from app.crud.user import get_user_by_email
from app.crud.expert import get_expert_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])

# User/ExpertログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
# 一時的に監査ログデコレーターを無効化
# @continuous_verification_audit(
#     event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
#     resource="auth",
#     action="login",
#     user_type="user",
#     session_id_key="session_id"
# )
@router.post("/login")
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
    resource="auth",
    action="login",
    user_type="user",
    session_id_key="session_id"
)
def login_user(
    http_request: Request, 
    request: LoginRequest, 
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_auth_login_rate_limit)
):
    
    # デバッグログを追加
    print(" ログイン関数が呼び出されました")
    print(f"🔍 リクエストIP: {http_request.client.host if http_request.client else 'unknown'}")

    # 監査サービスの初期化
    audit_service = AuditService(db)

    try:
        # 修正：暗号化されたメールアドレスでユーザーを検索
        user = get_user_by_email(db, request.email)

        # ユーザーが存在して、パスワードが正しい場合
        if user and verify_password(request.password, user.password_hash):
                print(f"✅ ユーザー認証成功: {user.email}")

                # ユーザーの権限を取得
                user_permissions = RBACService.get_user_permissions(user)

                # セッション管理を使用してログイン
                session_create = SessionCreate(
                    user_id=str(user.id),
                    user_type="user",
                    permissions=list(user_permissions),
                    ip_address=http_request.client.host if http_request.client else None,
                    user_agent=http_request.headers.get("user-agent")
                )
                
                # セッション作成後、kwargsにsession_idを追加
                session_response = session_manager.create_session(session_create)
                
                # 継続監視用のsession_idをkwargsに追加（安全な方法）
                try:
                    # 現在のフレームを安全に取得
                    current_frame = inspect.currentframe()
                    if current_frame and current_frame.f_back:
                        # フレームのローカル変数にsession_idを追加
                        frame_locals = current_frame.f_back.f_locals
                        if 'kwargs' in frame_locals:
                            frame_locals['kwargs']['session_id'] = session_response.session_id
                except Exception as e:
                    # inspectエラーが発生しても認証処理は継続
                    print(f"⚠️ 継続監視用session_id設定でエラー: {e}")
                    pass
                
                # 成功時の監査ログ
                try:
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
                    print("✅ 監査ログの保存に成功")
                except Exception as audit_error:
                    print(f"⚠️ 監査ログの保存に失敗: {audit_error}")
                    # 監査ログの保存に失敗しても認証処理は継続
                    pass
                
                return {
                    "access_token": session_response.access_token,
                    "refresh_token": session_response.refresh_token,
                    "session_id": session_response.session_id,
                    "expires_in": session_response.expires_in,
                    "token_type": session_response.token_type,
                    "user_type": "user",
                    "role": user.role
                }
        else:
            # 修正: userがNoneの場合を考慮
            if user:
                print(f"❌ ユーザーパスワード検証失敗: {user.email}")
            else:
                print(f"❌ ユーザーが見つかりません: {request.email}")
        
        # Userで見つからない場合、Expertテーブルで検索
        if not user:
            expert = get_expert_by_email(db, request.email)
            if expert and verify_password(request.password, expert.password_hash):

                # デバッグログを追加
                print(f"🔍 Expert認証成功: {expert.email}")
                print(f"🔍 Expert role: {expert.role}")
                print(f"🔍 Expert role type: {type(expert.role)}")

                try:
                    # Expertの権限を取得
                    expert_permissions = RBACService.get_expert_permissions(expert)
                    print(f" Expert permissions: {expert_permissions}")
                except Exception as e:
                    print(f"❌ Expert権限取得エラー: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Expert権限の取得に失敗しました: {str(e)}"
                    )

                # セッション管理を使用してログイン
                session_create = SessionCreate(
                    user_id=str(expert.id),
                    user_type="expert",
                    permissions=list(expert_permissions),
                    ip_address=http_request.client.host if http_request.client else None,
                    user_agent=http_request.headers.get("user-agent")
                )
                
                # セッション作成後、kwargsにsession_idを追加
                session_response = session_manager.create_session(session_create)
                
                # 継続監視用のsession_idをkwargsに追加（安全な方法）
                try:
                    # 現在のフレームを安全に取得
                    current_frame = inspect.currentframe()
                    if current_frame and current_frame.f_back:
                        # フレームのローカル変数にsession_idを追加
                        frame_locals = current_frame.f_back.f_locals
                        if 'kwargs' in frame_locals:
                            frame_locals['kwargs']['session_id'] = session_response.session_id
                except Exception as e:
                    # inspectエラーが発生しても認証処理は継続
                    print(f"⚠️ 継続監視用session_id設定でエラー: {e}")
                    pass
                
                # 成功時の監査ログ
                try:
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
                    print("✅ 監査ログの保存に成功")
                except Exception as audit_error:
                    print(f"⚠️ 監査ログの保存に失敗: {audit_error}")
                    # 監査ログの保存に失敗しても認証処理は継続
                    pass
                
                return {
                    "access_token": session_response.access_token,
                    "refresh_token": session_response.refresh_token,
                    "session_id": session_response.session_id,
                    "expires_in": session_response.expires_in,
                    "token_type": session_response.token_type,
                    "user_type": "expert",
                    "role": expert.role
                }
            else:
                # 修正: expertがNoneの場合を考慮
                if expert:
                    print(f"❌ Expertパスワード検証失敗: {expert.email}")
                else:
                    print(f"❌ Expertが見つかりません: {request.email}")
        
        # どちらでも認証失敗
        print(f"❌ 認証失敗: {request.email}")
        
        # 認証失敗時の監査ログ
        try:
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
            print("✅ 認証失敗の監査ログ保存完了")
        except Exception as audit_error:
            print(f"⚠️ 認証失敗時の監査ログ保存に失敗: {audit_error}")
            pass
    
        # どちらでも認証失敗
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    except HTTPException:
        # HTTPExceptionは再発生させる（認証失敗など）
        raise
    except Exception as e:
        # 予期しないエラーのみ監査ログに記録
        print(f"❌ 認証処理で予期しないエラー: {e}")
        print(f"❌ エラーの型: {type(e)}")
        
        # 予期しないエラーの監査ログ（エラーハンドリングを追加）
        try:
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
        except Exception as audit_error:
            print(f"⚠️ エラー時の監査ログ保存に失敗: {audit_error}")
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証処理中にエラーが発生しました。"
        )


# リフレッシュトークン用のリクエストモデルを追加
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# リフレッシュトークンを使用してアクセストークンを更新
@router.post("/refresh")
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
    resource="auth",
    action="refresh"
)
async def refresh_token(request: RefreshTokenRequest):
    """リフレッシュトークンを使用してアクセストークンを更新"""

    refresh_token = request.refresh_token  # 直接アクセス
    
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
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGOUT,
    resource="auth",
    action="logout"
)
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

@router.post("/decrypt-test")
def decrypt_test():
    """一時的な復号化テストエンドポイント"""
    try:
        encrypted_data = "gAAAAABooygSf3FW42gSAEEQEyEBclJbvH0M39v_hkOHZ5LDfen1s_8a-YoAiweBImunnD7bV-vMMuptIZAaAH0-Wj06t64m6ACJUrier-oln15qlxt-moQ="
        
        from app.core.security.encryption.service import encryption_service
        decrypted_data = encryption_service.decrypt_data(encrypted_data)  # decrypt → decrypt_data に修正
        
        return {"success": True, "decrypted": decrypted_data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/debug-users")
def debug_users(db: Session = Depends(get_db)):
    """デバッグ用：ユーザーデータの状態を確認"""
    try:
        users = db.query(User).limit(5).all()
        experts = db.query(Expert).limit(5).all()
        
        user_data = []
        for user in users:
            user_data.append({
                "id": str(user.id),
                "email": user.email,
                "email_length": len(user.email) if user.email else 0,
                "password_hash": user.password_hash[:20] + "..." if user.password_hash else None
            })
            
        expert_data = []
        for expert in experts:
            expert_data.append({
                "id": str(expert.id),
                "email": expert.email,
                "email_length": len(expert.email) if expert.email else 0,
                "password_hash": expert.password_hash[:20] + "..." if expert.password_hash else None
            })
            
        return {
            "users": user_data,
            "experts": expert_data
        }
    except Exception as e:
        return {"error": str(e)}